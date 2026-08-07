import json
import posixpath
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from core.storage import client as storage

from .exceptions import NpcNotFoundError
from .paths import _bucket, _cache_dir, _npc_prefix


# LanceDB's on-disk format is append-only - every memory write adds new version/
# transaction/index files and never removes old ones, so a NPC's memory/ dir only
# grows over a conversation. Tracks, per (user_id, slug), which relative paths under
# it are already known to exist in storage (either downloaded from there by
# ensure_cached, or uploaded by a prior sync_memory call this process), so
# sync_memory only has to push genuinely new files instead of re-uploading the
# NPC's entire memory history on every single message.
_synced_memory_paths: dict[tuple[str, str], set[str]] = defaultdict(set)


def ensure_cached(user_id: str, slug: str) -> Path:
    """Sync the NPC's files from storage into the local execution cache, if not already there.

    crewAI's loader needs real files on disk (it resolves the `skills` path relative to
    the project directory and opens the LanceDB memory table there), so NPCs can't run
    directly out of storage - the cache is what `/talk` actually executes against.
    """
    cache_dir = _cache_dir(user_id, slug)
    if (cache_dir / 'npc.json').exists():
        return cache_dir

    prefix = _npc_prefix(user_id, slug)
    keys = storage.list_files(_bucket(), prefix)
    if not keys:
        raise NpcNotFoundError(slug)

    already_synced = _synced_memory_paths[(user_id, slug)]
    for key in keys:
        rel = key[len(prefix):]
        if not rel:
            continue
        dest = cache_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if rel.startswith('memory/'):
            # LanceDB fragment files are binary - route them through the file-based
            # upload/download calls instead of the utf-8 text ones used for everything else.
            storage.download(_bucket(), key, str(dest))
            # Already in storage by definition - sync_memory shouldn't push it back up.
            already_synced.add(rel)
        else:
            dest.write_text(storage.get_text(_bucket(), key), encoding='utf-8')

    return cache_dir


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
    cache_dir = _cache_dir(user_id, slug)
    memory_dir = cache_dir / 'memory'
    if not memory_dir.is_dir():
        return

    prefix = _npc_prefix(user_id, slug)
    already_synced = _synced_memory_paths[(user_id, slug)]
    for path in memory_dir.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(cache_dir).as_posix()
        if rel in already_synced:
            continue
        storage.upload(_bucket(), prefix + rel, str(path))
        already_synced.add(rel)


def append_turn(user_id: str, slug: str, fields: dict) -> None:
    """Append one conversation turn to today's session transcript and push it to storage.

    This is a different kind of persistence than sync_memory: crewAI's Memory is a
    heuristic summary an NPC recalls, this is the raw record of what was actually
    said - kept for debugging/moderation review, and left alone by
    reset_npc_memory (forgetting what the NPC "knows" shouldn't erase what
    happened). Rotated by UTC date so one NPC's transcript never grows into a
    single unbounded file over its lifetime.

    Unlike sync_memory's fragment-level dedup (LanceDB writes many small immutable
    files, so only-upload-what's-new actually matters), there's exactly one file
    in play here and it's small - one NPC's turns for one day - so it's simplest
    to just re-read and re-upload the whole thing after every turn, the same plain
    overwrite `_write_file` already uses for npc.json/SKILL.md. Supabase Storage's
    S3-compatible API has no append/patch operation to exploit anyway.
    """
    now = datetime.now(timezone.utc)
    rel_path = f"sessions/{now.strftime('%Y-%m-%d')}.jsonl"
    local_path = _cache_dir(user_id, slug) / rel_path
    local_path.parent.mkdir(parents=True, exist_ok=True)

    record = {'ts': now.isoformat(), **fields}
    with local_path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(record) + '\n')

    storage_key = posixpath.normpath(_npc_prefix(user_id, slug) + rel_path)
    storage.put_text(_bucket(), storage_key, local_path.read_text(encoding='utf-8'))


def _write_file(user_id: str, slug: str, rel_path: str, content: str) -> None:
    local_path = _cache_dir(user_id, slug) / rel_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(content, encoding='utf-8')
    # normalize away '..' segments (e.g. rel_path='../__init__.py'): Supabase Storage's
    # Cloudflare front collapses '..' in the URL path before it reaches the S3-compatible
    # origin, which no longer matches the path boto3 signed -> SignatureDoesNotMatch.
    storage_key = posixpath.normpath(_npc_prefix(user_id, slug) + rel_path)
    storage.put_text(_bucket(), storage_key, content)
