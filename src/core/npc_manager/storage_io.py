import json
import posixpath
from datetime import datetime, timezone
from pathlib import Path

from core.storage import client as storage

from .exceptions import NpcNotFoundError
from .paths import _bucket, _cache_dir, _npc_prefix


# The NPC's conversational memory: a rolling window of recent turns fed back into the
# prompt as chat history. Lives under memory/ so reset_npc_memory (which deletes that
# prefix) makes the NPC forget, while sessions/ transcripts are left alone.
_MEMORY_TURNS_PATH = 'memory/turns.jsonl'
# Cap on what's kept in that file - it's re-uploaded whole after every turn, so it
# must not grow without bound. Comfortably above Config.NPC_HISTORY_TURNS.
_MEMORY_TURNS_KEPT = 100


def ensure_cached(user_id: str, slug: str) -> Path:
    """Sync the NPC's files from storage into the local execution cache, if not already there.

    /talk reads the NPC's skills and memory from the local cache dir rather than
    storage, so a message never waits on a storage round trip for them.
    """
    cache_dir = _cache_dir(user_id, slug)
    if (cache_dir / 'npc.json').exists():
        return cache_dir

    prefix = _npc_prefix(user_id, slug)
    keys = storage.list_files(_bucket(), prefix)
    if not keys:
        raise NpcNotFoundError(slug)

    for key in keys:
        rel = key[len(prefix):]
        if not rel:
            continue
        if rel.startswith('memory/') and rel != _MEMORY_TURNS_PATH:
            # Leftover LanceDB fragments from the crewAI Memory era - nothing reads
            # them anymore, so don't pay to download them.
            continue
        dest = cache_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(storage.get_text(_bucket(), key), encoding='utf-8')

    return cache_dir


def load_recent_turns(user_id: str, slug: str, limit: int) -> list[dict]:
    """The last `limit` turns of the NPC's memory, oldest first."""
    path = _cache_dir(user_id, slug) / _MEMORY_TURNS_PATH
    if limit <= 0 or not path.exists():
        return []
    lines = [line for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    return [json.loads(line) for line in lines[-limit:]]


def append_turn(user_id: str, slug: str, fields: dict) -> None:
    """Record one conversation turn in both the NPC's memory and today's session transcript.

    Two different kinds of persistence: memory/turns.jsonl is what the NPC recalls
    (trimmed to a rolling window, wiped by reset_npc_memory), sessions/ is the raw
    record of what was actually said - kept for debugging/moderation review and left
    alone by reset_npc_memory (forgetting what the NPC "knows" shouldn't erase what
    happened). Sessions are rotated by UTC date so one NPC's transcript never grows
    into a single unbounded file over its lifetime.

    Both files are small, so each is just re-uploaded whole after every turn - the same
    plain overwrite `_write_file` already uses for npc.json/SKILL.md. Supabase Storage's
    S3-compatible API has no append/patch operation to exploit anyway.
    """
    now = datetime.now(timezone.utc)
    line = json.dumps({'ts': now.isoformat(), **fields}) + '\n'
    cache_dir = _cache_dir(user_id, slug)

    memory_path = cache_dir / _MEMORY_TURNS_PATH
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    existing = memory_path.read_text(encoding='utf-8').splitlines(keepends=True) if memory_path.exists() else []
    memory_path.write_text(''.join([*existing, line][-_MEMORY_TURNS_KEPT:]), encoding='utf-8')

    session_rel = f"sessions/{now.strftime('%Y-%m-%d')}.jsonl"
    session_path = cache_dir / session_rel
    session_path.parent.mkdir(parents=True, exist_ok=True)
    with session_path.open('a', encoding='utf-8') as f:
        f.write(line)

    for rel_path, local_path in ((_MEMORY_TURNS_PATH, memory_path), (session_rel, session_path)):
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
