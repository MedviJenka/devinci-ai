import json
import keyword
import posixpath
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal
from crewai import Agent, Memory
from pydantic import BaseModel, Field, create_model
from core.settings import Config
from core.storage import client as storage


DEFAULT_LLM = 'openai/gpt-5.5'

_FIELD_TYPES: dict[str, type] = {'string': str, 'integer': int, 'float': float, 'boolean': bool}

_DEFAULT_PERSONA_NOTES = '''# {display_name}

**Age:**
**Occupation:**

## Backstory

{backstory}

## Personality

-

## Known Facts

-
'''

_STRICT_RULES = '''**STRICT RULES**
- no sexual content
- if the user annoys you, respond with: "I don't want to talk to you anymore... come back later when I calm down"'''

_SKILL_MD = '''---
name: {slug}
description: {description}
---

''' + _STRICT_RULES + '''

{persona_notes}
'''


# LanceDB's on-disk format is append-only - every memory write adds new version/
# transaction/index files and never removes old ones, so a NPC's memory/ dir only
# grows over a conversation. Tracks, per (user_id, slug), which relative paths under
# it are already known to exist in storage (either downloaded from there by
# ensure_cached, or uploaded by a prior sync_memory call this process), so
# sync_memory only has to push genuinely new files instead of re-uploading the
# NPC's entire memory history on every single message.
_synced_memory_paths: dict[tuple[str, str], set[str]] = defaultdict(set)


class NpcNotFoundError(Exception):
    pass


class NpcAlreadyExistsError(Exception):
    pass


class PydanticFieldDef(BaseModel):
    name: str
    type: Literal['string', 'integer', 'float', 'boolean', 'enum']
    description: str = ''
    enum_values: list[str] = Field(default_factory=list)
    required: bool = True


def _default_pydantic_fields() -> list[PydanticFieldDef]:
    return [
        PydanticFieldDef(
            name='mood', type='enum', description='current npc mood based on the given prompt',
            enum_values=['Angry', 'Sad', 'Happy', 'Furious', 'Calm'], required=True,
        ),
        PydanticFieldDef(name='response', type='string', description='npc response, rely also on memory', required=True),
    ]


class NpcSummary(BaseModel):
    slug: str
    role: str
    goal: str
    llm: str


class NpcDetail(NpcSummary):
    backstory: str
    persona_notes: str
    pydantic_enabled: bool
    pydantic_fields: list[PydanticFieldDef]


class NpcCreateRequest(BaseModel):
    name: str
    goal: str = Field(default='interactive npc')
    backstory: str = Field(default='')
    llm: str = Field(default=Config.OPENAI_MODEL)
    persona_notes: str = Field(default='')


class NpcUpdateRequest(BaseModel):
    goal: str | None = None
    backstory: str | None = None
    llm: str | None = None
    persona_notes: str | None = None
    pydantic_enabled: bool | None = None
    pydantic_fields: list[PydanticFieldDef] | None = None


def slugify(name: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '_', name.strip().lower()).strip('_')
    if not slug:
        raise ValueError('name must contain at least one alphanumeric character')
    return slug


def _bucket() -> str:
    return Config.NPC_STORAGE_BUCKET


def _user_prefix(user_id: str) -> str:
    return f'{user_id}/'


def _npc_prefix(user_id: str, slug: str) -> str:
    return f'{user_id}/{slug}/'


def _cache_dir(user_id: str, slug: str) -> Path:
    return Path(Config.NPC_CACHE_DIR) / user_id / slug


def _validate_pydantic_fields(fields: list[PydanticFieldDef]) -> None:
    seen: set[str] = set()
    for field in fields:
        name = field.name
        if not name.isidentifier():
            raise ValueError(f"'{name}' is not a valid field name")
        if keyword.iskeyword(name):
            raise ValueError(f"'{name}' is a reserved Python keyword")
        if name.startswith('_'):
            raise ValueError(f"'{name}' must not start with an underscore")
        if name.startswith('model_'):
            raise ValueError(f"'{name}' collides with pydantic's protected 'model_' namespace")
        if name in seen:
            raise ValueError(f"duplicate field name '{name}'")
        seen.add(name)
        if field.type == 'enum' and not field.enum_values:
            raise ValueError(f"field '{name}' of type enum needs at least one enum value")


def build_response_schema(fields: list[PydanticFieldDef]) -> type[BaseModel]:
    """Build an NPC's structured-output schema at runtime from its field defs, instead
    of generating and re-parsing a `class NpcResponseSchema(BaseModel): ...` source block."""
    definitions: dict[str, Any] = {}
    for field in fields:
        annotation: Any = Literal[tuple(field.enum_values)] if field.type == 'enum' else _FIELD_TYPES[field.type]
        if not field.required:
            annotation = annotation | None
        default = ... if field.required else None
        definitions[field.name] = (annotation, Field(default, description=field.description))
    return create_model('NpcResponseSchema', **definitions)


def build_agent(cache_dir: Path, npc: NpcDetail) -> Agent:
    """Construct the crewAI Agent for a cached NPC.

    Constructing the LLM client and opening the LanceDB memory table (connect +
    schema/index checks) is expensive enough to dominate response latency if repeated
    on every message - callers should build this once per process and reuse it.
    """
    return Agent(
        role=npc.role, goal=npc.goal, backstory=npc.backstory,
        llm={'model': npc.llm},
        skills=[str(cache_dir / 'skills')],
        memory=Memory(storage=str(cache_dir / 'memory')),
    )


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


def _split_skill_md(text: str) -> tuple[str, str]:
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', text, flags=re.DOTALL)
    if not match:
        return '', text
    frontmatter, body = match.groups()
    description = ''
    for line in frontmatter.splitlines():
        if line.startswith('description:'):
            description = line.split(':', 1)[1].strip()

    body = body.strip('\n')
    if body.startswith(_STRICT_RULES):
        body = body[len(_STRICT_RULES):].strip('\n')
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


def _write_file(user_id: str, slug: str, rel_path: str, content: str) -> None:
    local_path = _cache_dir(user_id, slug) / rel_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(content, encoding='utf-8')
    # normalize away '..' segments (e.g. rel_path='../__init__.py'): Supabase Storage's
    # Cloudflare front collapses '..' in the URL path before it reaches the S3-compatible
    # origin, which no longer matches the path boto3 signed -> SignatureDoesNotMatch.
    storage_key = posixpath.normpath(_npc_prefix(user_id, slug) + rel_path)
    storage.put_text(_bucket(), storage_key, content)


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
