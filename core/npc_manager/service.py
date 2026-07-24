import json
import shutil
from collections import defaultdict
from pathlib import Path
from core.storage import client as storage
from core.npc_manager.exceptions import NpcAlreadyExistsError, NpcNotFoundError
from core.npc_manager.paths import bucket, cache_dir, npc_prefix, user_prefix
from core.npc_manager.schemas import NpcCreateRequest, NpcDetail, NpcSummary, NpcUpdateRequest, _default_pydantic_fields
from core.npc_manager.storage_io import (
    parse_npc_config,
    prune_legacy_files,
    skill_md_key,
    split_skill_md,
    write_file,
    write_npc_config,
    write_skill_md,
)
from core.npc_manager.templates import DEFAULT_PERSONA_NOTES, LEGACY_FILES
from core.npc_manager.validation import slugify


# LanceDB's on-disk format is append-only - every memory write adds new version/
# transaction/index files and never removes old ones, so a NPC's memory/ dir only
# grows over a conversation. Tracks, per (user_id, slug), which relative paths under
# it are already known to exist in storage (either downloaded from there by
# ensure_cached, or uploaded by a prior sync_memory call this process), so
# sync_memory only has to push genuinely new files instead of re-uploading the
# NPC's entire memory history on every single message.
_synced_memory_paths: dict[tuple[str, str], set[str]] = defaultdict(set)


def list_npcs(user_id: str) -> list[NpcSummary]:
    summaries = []
    for prefix in sorted(storage.list_prefixes(bucket(), user_prefix(user_id))):
        slug = prefix.rstrip('/').rsplit('/', 1)[-1]
        if slug.startswith('_') or not storage.exists(bucket(), prefix + 'npc.json'):
            continue
        try:
            summaries.append(_read_summary(user_id, slug))
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            continue
    return summaries


def _read_summary(user_id: str, slug: str) -> NpcSummary:
    config = parse_npc_config(storage.get_text(bucket(), npc_prefix(user_id, slug) + 'npc.json'))
    return NpcSummary(slug=slug, role=config['role'], goal=config['goal'], llm=config['llm'])


def get_npc(user_id: str, slug: str) -> NpcDetail:
    prefix = npc_prefix(user_id, slug)
    if not storage.exists(bucket(), prefix + 'npc.json'):
        raise NpcNotFoundError(slug)

    config = parse_npc_config(storage.get_text(bucket(), prefix + 'npc.json'))

    key = skill_md_key(user_id, slug)
    persona_notes = split_skill_md(storage.get_text(bucket(), key))[1] if key else ''

    return NpcDetail(
        slug=slug,
        role=config['role'],
        goal=config['goal'],
        llm=config['llm'],
        backstory=config['backstory'],
        persona_notes=persona_notes,
        pydantic_enabled=config['pydantic_enabled'],
        pydantic_fields=config['pydantic_fields'],
    )


def create_npc(user_id: str, req: NpcCreateRequest) -> NpcDetail:
    slug = slugify(req.name)
    if storage.exists(bucket(), npc_prefix(user_id, slug) + 'npc.json'):
        raise NpcAlreadyExistsError(slug)

    # A stale local cache dir (e.g. left behind by a crash between create and delete)
    # would otherwise let a new NPC inherit an old memory/ LanceDB store from a
    # previous NPC that happened to reuse this slug.
    local_cache_dir = cache_dir(user_id, slug)
    if local_cache_dir.exists():
        shutil.rmtree(local_cache_dir)

    write_file(user_id, slug, '../__init__.py', '')

    persona_notes = req.persona_notes.strip() or DEFAULT_PERSONA_NOTES.format(
        display_name=req.name, backstory=req.backstory or 'No backstory written yet.',
    )
    write_npc_config(user_id, slug, req.goal, req.backstory, req.llm, True, _default_pydantic_fields())
    write_skill_md(user_id, slug, slug, req.goal, persona_notes)

    return get_npc(user_id, slug)


def update_npc(user_id: str, slug: str, req: NpcUpdateRequest) -> NpcDetail:
    current = get_npc(user_id, slug)

    goal = req.goal if req.goal is not None else current.goal
    backstory = req.backstory if req.backstory is not None else current.backstory
    llm = req.llm if req.llm is not None else current.llm
    persona_notes = req.persona_notes if req.persona_notes is not None else current.persona_notes
    enabled = req.pydantic_enabled if req.pydantic_enabled is not None else current.pydantic_enabled
    fields = req.pydantic_fields if req.pydantic_fields is not None else current.pydantic_fields

    existing_skill_key = skill_md_key(user_id, slug)
    skill_dir_name = existing_skill_key.rsplit('/', 2)[-2] if existing_skill_key else slug

    # Rewritten unconditionally (not just on creation) so existing NPCs pick up template
    # fixes - e.g. the per-NPC memory wiring - the next time they're edited, instead of
    # being stuck forever with whatever config existed when they were first created.
    write_npc_config(user_id, slug, goal, backstory, llm, enabled, fields)
    write_skill_md(user_id, slug, skill_dir_name, goal, persona_notes)

    prune_legacy_files(user_id, slug)

    # The execution cache (see ensure_cached) only ever syncs missing files, so without
    # clearing it here an already-cached NPC would keep serving whatever config it had
    # at first talk, silently ignoring every edit made after that.
    local_cache_dir = cache_dir(user_id, slug)
    if local_cache_dir.exists():
        shutil.rmtree(local_cache_dir)

    return get_npc(user_id, slug)


def delete_npc(user_id: str, slug: str) -> None:
    prefix = npc_prefix(user_id, slug)
    if not storage.exists(bucket(), prefix + 'npc.json'):
        raise NpcNotFoundError(slug)
    storage.delete_prefix(bucket(), prefix)

    local_cache_dir = cache_dir(user_id, slug)
    if local_cache_dir.exists():
        shutil.rmtree(local_cache_dir)
    _synced_memory_paths.pop((user_id, slug), None)


def ensure_cached(user_id: str, slug: str) -> Path:
    """Sync the NPC's files from storage into the local execution cache, if not already there.

    crewAI's loader needs real files on disk (it resolves the `skills` path relative to
    the project directory and opens the LanceDB memory table there), so NPCs can't run
    directly out of storage - the cache is what `/talk` actually executes against.
    """
    local_cache_dir = cache_dir(user_id, slug)
    if (local_cache_dir / 'npc.json').exists():
        return local_cache_dir

    prefix = npc_prefix(user_id, slug)
    keys = storage.list_files(bucket(), prefix)
    if not keys:
        raise NpcNotFoundError(slug)

    already_synced = _synced_memory_paths[(user_id, slug)]
    for key in keys:
        rel = key[len(prefix):]
        if not rel or rel in LEGACY_FILES:
            continue
        dest = local_cache_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if rel.startswith('memory/'):
            # LanceDB fragment files are binary - route them through the file-based
            # upload/download calls instead of the utf-8 text ones used for everything else.
            storage.download(bucket(), key, str(dest))
            # Already in storage by definition - sync_memory shouldn't push it back up.
            already_synced.add(rel)
        else:
            dest.write_text(storage.get_text(bucket(), key), encoding='utf-8')

    return local_cache_dir


def sync_memory(user_id: str, slug: str) -> None:
    """Push an NPC's local LanceDB memory files up to storage after a conversation.

    crewAI's memory only ever writes to the local cache dir (see `ensure_cached`), so
    without this a fresh cache - a different instance, or this one after eviction - would
    come back with no memory of prior conversations.

    LanceDB's format is append-only (every write adds new version/transaction/index
    files and never touches old ones), so memory_dir only grows over a conversation.
    Re-uploading the whole thing on every call would make each successive message
    slower than the last as history piles up - only files not already known to be in
    storage get uploaded.
    """
    local_cache_dir = cache_dir(user_id, slug)
    memory_dir = local_cache_dir / 'memory'
    if not memory_dir.is_dir():
        return

    prefix = npc_prefix(user_id, slug)
    already_synced = _synced_memory_paths[(user_id, slug)]
    for path in memory_dir.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(local_cache_dir).as_posix()
        if rel in already_synced:
            continue
        storage.upload(bucket(), prefix + rel, str(path))
        already_synced.add(rel)
