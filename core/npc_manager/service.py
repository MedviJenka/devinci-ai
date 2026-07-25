import json
import re
import shutil
from typing import Any
from core.storage import client as storage
from .exceptions import NpcAlreadyExistsError, NpcNotFoundError
from .paths import _bucket, _cache_dir, _npc_prefix, _user_prefix, slugify
from .schemas import (
    NpcCreateRequest,
    NpcDetail,
    NpcSummary,
    NpcUpdateRequest,
    PydanticFieldDef,
    _default_pydantic_fields,
)
from .storage_io import _synced_memory_paths, _write_file
from .templates import _DEFAULT_PERSONA_NOTES, _SKILL_MD, _STRICT_RULES
from .validation import _validate_pydantic_fields


def _render_npc_config(
    role: str, goal: str, backstory: str, llm: str, enabled: bool, fields: list[PydanticFieldDef],
) -> str:
    return json.dumps({
        'role': role,
        'goal': goal,
        'backstory': backstory,
        'llm': llm,
        'pydantic_enabled': enabled,
        'pydantic_fields': [field.model_dump() for field in fields],
    }, indent=2)


def _parse_npc_config(text: str) -> dict[str, Any]:
    data = json.loads(text)
    data['pydantic_fields'] = [PydanticFieldDef(**field) for field in data['pydantic_fields']]
    return data


def _skill_md_key(user_id: str, slug: str) -> str | None:
    prefix = _npc_prefix(user_id, slug) + 'skills/'
    for key in storage.list_files(_bucket(), prefix):
        if key.endswith('/SKILL.md'):
            return key
    return None


_STRICT_RULES_BLOCK_RE = re.compile(
    rf'^{re.escape(_STRICT_RULES.splitlines()[0])}\n(?:-.*\n?)*\n*',
)


def _split_skill_md(text: str) -> tuple[str, str]:
    # _SKILL_MD's template literally starts with a blank line before the opening
    # "---", so anchoring this match at the exact start of the string always failed
    # to find the frontmatter - _split_skill_md silently returned the whole file
    # (frontmatter, STRICT_RULES, and all) as "persona_notes" on every read, which then
    # got wrapped in a brand new frontmatter+STRICT_RULES shell on every single save,
    # compounding indefinitely. Tolerating leading whitespace here is what actually
    # lets stripping happen at all.
    match = re.match(r'^\s*---\n(.*?)\n---\n(.*)$', text, flags=re.DOTALL)
    if not match:
        return '', text
    frontmatter, body = match.groups()
    description = ''
    for line in frontmatter.splitlines():
        if line.startswith('description:'):
            description = line.split(':', 1)[1].strip()

    body = body.strip('\n')
    # _write_skill_md always prepends a fresh _STRICT_RULES block on save. A single
    # exact-match strip here means any drift from that literal string (e.g. an edit
    # landing near/inside the block) leaves stale copies embedded as ordinary body
    # text, which then get ANOTHER fresh block prepended on the next save - silently
    # compounding duplicates. Strip every leading occurrence of the block shape (its
    # header line followed by "-" bullet lines), not just one literal match, so
    # accumulated duplicates self-heal instead of growing.
    while True:
        block_match = _STRICT_RULES_BLOCK_RE.match(body)
        if not block_match:
            break
        body = body[block_match.end():].lstrip('\n')
    return description, body


def list_npcs(user_id: str) -> list[NpcSummary]:
    summaries = []
    for prefix in sorted(storage.list_prefixes(_bucket(), _user_prefix(user_id))):
        slug = prefix.rstrip('/').rsplit('/', 1)[-1]
        if slug.startswith('_') or not storage.exists(_bucket(), prefix + 'npc.json'):
            continue
        try:
            summaries.append(_read_summary(user_id, slug))
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            continue
    return summaries


def _read_summary(user_id: str, slug: str) -> NpcSummary:
    config = _parse_npc_config(storage.get_text(_bucket(), _npc_prefix(user_id, slug) + 'npc.json'))
    return NpcSummary(slug=slug, role=config['role'], goal=config['goal'], llm=config['llm'])


def get_npc(user_id: str, slug: str) -> NpcDetail:
    prefix = _npc_prefix(user_id, slug)
    if not storage.exists(_bucket(), prefix + 'npc.json'):
        raise NpcNotFoundError(slug)

    config = _parse_npc_config(storage.get_text(_bucket(), prefix + 'npc.json'))

    skill_key = _skill_md_key(user_id, slug)
    persona_notes = _split_skill_md(storage.get_text(_bucket(), skill_key))[1] if skill_key else ''

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
    if storage.exists(_bucket(), _npc_prefix(user_id, slug) + 'npc.json'):
        raise NpcAlreadyExistsError(slug)

    # A stale local cache dir (e.g. left behind by a crash between create and delete)
    # would otherwise let a new NPC inherit an old memory/ LanceDB store from a
    # previous NPC that happened to reuse this slug.
    cache_dir = _cache_dir(user_id, slug)
    if cache_dir.exists():
        shutil.rmtree(cache_dir)

    _write_file(user_id, slug, '../__init__.py', '')

    persona_notes = req.persona_notes.strip() or _DEFAULT_PERSONA_NOTES.format(
        display_name=req.name, backstory=req.backstory or 'No backstory written yet.',
    )
    _write_npc_config(user_id, slug, req.goal, req.backstory, req.llm, True, _default_pydantic_fields())
    _write_skill_md(user_id, slug, slug, req.goal, persona_notes)

    return get_npc(user_id, slug)


def update_npc(user_id: str, slug: str, req: NpcUpdateRequest) -> NpcDetail:
    current = get_npc(user_id, slug)

    goal = req.goal if req.goal is not None else current.goal
    backstory = req.backstory if req.backstory is not None else current.backstory
    llm = req.llm if req.llm is not None else current.llm
    persona_notes = req.persona_notes if req.persona_notes is not None else current.persona_notes
    enabled = req.pydantic_enabled if req.pydantic_enabled is not None else current.pydantic_enabled
    fields = req.pydantic_fields if req.pydantic_fields is not None else current.pydantic_fields

    existing_skill_key = _skill_md_key(user_id, slug)
    skill_dir_name = existing_skill_key.rsplit('/', 2)[-2] if existing_skill_key else slug

    # Rewritten unconditionally (not just on creation) so existing NPCs pick up template
    # fixes - e.g. the per-NPC memory wiring - the next time they're edited, instead of
    # being stuck forever with whatever config existed when they were first created.
    _write_npc_config(user_id, slug, goal, backstory, llm, enabled, fields)
    _write_skill_md(user_id, slug, skill_dir_name, goal, persona_notes)

    # The execution cache (see ensure_cached) only ever syncs missing files, so without
    # clearing it here an already-cached NPC would keep serving whatever config it had
    # at first talk, silently ignoring every edit made after that.
    cache_dir = _cache_dir(user_id, slug)
    if cache_dir.exists():
        shutil.rmtree(cache_dir)

    return get_npc(user_id, slug)


def delete_npc(user_id: str, slug: str) -> None:
    prefix = _npc_prefix(user_id, slug)
    if not storage.exists(_bucket(), prefix + 'npc.json'):
        raise NpcNotFoundError(slug)
    storage.delete_prefix(_bucket(), prefix)

    cache_dir = _cache_dir(user_id, slug)
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    _synced_memory_paths.pop((user_id, slug), None)


def reset_npc_memory(user_id: str, slug: str) -> None:
    prefix = _npc_prefix(user_id, slug)
    if not storage.exists(_bucket(), prefix + 'npc.json'):
        raise NpcNotFoundError(slug)
    storage.delete_prefix(_bucket(), prefix + 'memory/')

    memory_dir = _cache_dir(user_id, slug) / 'memory'
    if memory_dir.exists():
        shutil.rmtree(memory_dir)
    _synced_memory_paths.pop((user_id, slug), None)


def _write_npc_config(
    user_id: str, slug: str, goal: str, backstory: str, llm: str, enabled: bool, fields: list[PydanticFieldDef],
) -> None:
    _validate_pydantic_fields(fields)
    if enabled and not fields:
        raise ValueError('at least one field is required when structured output is enabled')
    content = _render_npc_config(role=slug, goal=goal, backstory=backstory, llm=llm, enabled=enabled, fields=fields)
    _write_file(user_id, slug, 'npc.json', content)


def _write_skill_md(user_id: str, slug: str, skill_dir_name: str, goal: str, persona_notes: str) -> None:
    content = _SKILL_MD.format(slug=skill_dir_name, description=goal, persona_notes=persona_notes.strip())
    _write_file(user_id, slug, f'skills/{skill_dir_name}/SKILL.md', content)
