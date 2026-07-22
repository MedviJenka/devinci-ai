import json
import keyword
import posixpath
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Literal
from crewai.project import strip_jsonc_comments
from pydantic import BaseModel, Field
from core.settings import Config
from core.storage import client as storage


DEFAULT_LLM = 'openai/gpt-5.5'

# Filenames written by code paths that no longer exist (an earlier structured-output
# implementation wrote 'schema.py' before it was reworked into 'schemas.py' +
# 'output_schema.jsonc'; 'voice.json' was per-NPC TTS settings for a feature not present
# on this branch). Nothing reads these; update_npc prunes them from storage/cache on touch.
_LEGACY_FILES = ('schema.py', 'voice.json')

_FIELD_TYPE_ANNOTATIONS = {
    'string': 'str',
    'integer': 'int',
    'float': 'float',
    'boolean': 'bool',
}

_SCHEMAS_PY_HEADER = '''
from typing import Literal
from pydantic import BaseModel, Field


class NpcResponseSchema(BaseModel):
'''

_NPC_PY = '''
import asyncio
from pathlib import Path
import core.ai.crewai_compat  # noqa: F401
from crewai.project import load_crew
from crewai.types.streaming import CrewStreamingOutput
from crewai.memory import Memory

_crew = None


def _get_crew():
    # Built once per process and cached - parsing crew.jsonc/agents, constructing the
    # LLM client, and opening the LanceDB memory table (connect + schema/index checks)
    # is expensive enough to dominate response latency if repeated on every message.
    # Safe to reuse across calls: api.py serializes calls to a given NPC with a lock,
    # so there's no concurrent kickoff on this same crew instance.
    global _crew
    if _crew is None:
        crew, _ = load_crew(Path(__file__).with_name('crew.jsonc'))
        # crew.jsonc's "memory": true would default to a store shared by every NPC in this
        # process (keyed off the project dir, not the NPC) - point it at this NPC's own cache
        # dir instead, then re-run the memory validator so crew._memory picks it up.
        crew.memory = Memory(storage=str(Path(__file__).with_name('memory')))
        crew.create_crew_memory()
        _crew = crew
    return _crew


async def main(prompt: str) -> CrewStreamingOutput:
    return await _get_crew().kickoff_async(inputs={'prompt': prompt})


async def _demo() -> None:
    streaming = await main('hello')
    async for chunk in streaming:
        print(chunk.content, end='')
    print()
    print(streaming.result.pydantic)


if __name__ == '__main__':
    asyncio.run(_demo())
'''

_README_MD = '''# {slug}

A crewAI project using JSON-first configuration, scaffolded by the NPC creator.

## Project Structure

- `agents/` - Agent definition (JSONC)
- `crew.jsonc` - Crew definition with tasks and configuration
- `skills/` - Persona / lore for the agent
'''

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


def _load_jsonc_text(text: str) -> Any:
    return json.loads(strip_jsonc_comments(text))


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


def _render_schemas_py(fields: list[PydanticFieldDef]) -> str:
    if not fields:
        body = '    pass\n'
    else:
        field_lines = []
        for field in fields:
            if field.type == 'enum':
                values = ', '.join(repr(v) for v in field.enum_values)
                annotation = f'Literal[{values}]'
            else:
                annotation = _FIELD_TYPE_ANNOTATIONS[field.type]
            if not field.required:
                annotation = f'{annotation} | None'
            default = '...' if field.required else 'None'
            field_lines.append(
                f'    {field.name}: {annotation} = Field({default}, description={field.description!r})',
            )
        body = '\n'.join(field_lines) + '\n'
    return _SCHEMAS_PY_HEADER + body


def _output_schema_key(user_id: str, slug: str) -> str:
    return _npc_prefix(user_id, slug) + 'output_schema.jsonc'


def _read_output_schema(user_id: str, slug: str) -> tuple[bool, list[PydanticFieldDef]]:
    key = _output_schema_key(user_id, slug)
    if not storage.exists(_bucket(), key):
        return True, _default_pydantic_fields()
    data = _load_jsonc_text(storage.get_text(_bucket(), key))
    fields = [PydanticFieldDef(**field) for field in data.get('fields', [])]
    return bool(data.get('enabled', True)), fields


def _write_output_schema(user_id: str, slug: str, enabled: bool, fields: list[PydanticFieldDef]) -> None:
    _validate_pydantic_fields(fields)
    if enabled and not fields:
        raise ValueError('at least one field is required when structured output is enabled')

    data = {'enabled': enabled, 'fields': [field.model_dump() for field in fields]}
    content = '// Structured output schema, edited via the NPC editor\n' + json.dumps(data, indent=2) + '\n'
    _write_file(user_id, slug, 'output_schema.jsonc', content)

    _write_file(user_id, slug, 'schemas.py', _render_schemas_py(fields))
    # crewai imports "schemas" by bare module name and caches it in sys.modules keyed only
    # by that name, not by path - without evicting it here, a re-generated schemas.py for
    # this NPC would silently keep serving the previous in-process import on the next /talk.
    sys.modules.pop('schemas', None)

    crew_key = _npc_prefix(user_id, slug) + 'crew.jsonc'
    crew = _load_jsonc_text(storage.get_text(_bucket(), crew_key))
    if enabled:
        crew['tasks'][0]['output_pydantic'] = {'python': 'schemas.NpcResponseSchema'}
    else:
        crew['tasks'][0].pop('output_pydantic', None)
    content = '// Crew definition, generated by the NPC creator\n' + json.dumps(crew, indent=2) + '\n'
    _write_file(user_id, slug, 'crew.jsonc', content)


def _agent_name_for(user_id: str, slug: str) -> str:
    crew = _load_jsonc_text(storage.get_text(_bucket(), _npc_prefix(user_id, slug) + 'crew.jsonc'))
    return crew['agents'][0]


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
        if slug.startswith('_') or not storage.exists(_bucket(), prefix + 'crew.jsonc'):
            continue
        try:
            summaries.append(_read_summary(user_id, slug))
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            continue
    return summaries


def _read_summary(user_id: str, slug: str) -> NpcSummary:
    agent_name = _agent_name_for(user_id, slug)
    agent = _load_jsonc_text(storage.get_text(_bucket(), _npc_prefix(user_id, slug) + f'agents/{agent_name}.jsonc'))
    return NpcSummary(slug=slug, role=agent['role'], goal=agent['goal'], llm=agent['llm'])


def get_npc(user_id: str, slug: str) -> NpcDetail:
    prefix = _npc_prefix(user_id, slug)
    if not storage.exists(_bucket(), prefix + 'crew.jsonc'):
        raise NpcNotFoundError(slug)

    agent_name = _agent_name_for(user_id, slug)
    agent = _load_jsonc_text(storage.get_text(_bucket(), prefix + f'agents/{agent_name}.jsonc'))

    skill_key = _skill_md_key(user_id, slug)
    persona_notes = _split_skill_md(storage.get_text(_bucket(), skill_key))[1] if skill_key else ''

    pydantic_enabled, pydantic_fields = _read_output_schema(user_id, slug)

    return NpcDetail(
        slug=slug,
        role=agent['role'],
        goal=agent['goal'],
        llm=agent['llm'],
        backstory=agent.get('backstory', ''),
        persona_notes=persona_notes,
        pydantic_enabled=pydantic_enabled,
        pydantic_fields=pydantic_fields,
    )


def create_npc(user_id: str, req: NpcCreateRequest) -> NpcDetail:
    slug = slugify(req.name)
    if storage.exists(_bucket(), _npc_prefix(user_id, slug) + 'crew.jsonc'):
        raise NpcAlreadyExistsError(slug)

    # A stale local cache dir (e.g. left behind by a crash between create and delete)
    # would otherwise let a new NPC inherit an old memory/ LanceDB store from a
    # previous NPC that happened to reuse this slug.
    cache_dir = _cache_dir(user_id, slug)
    if cache_dir.exists():
        shutil.rmtree(cache_dir)

    _write_file(user_id, slug, '../__init__.py', '')
    _write_file(user_id, slug, 'npc.py', _NPC_PY)
    _write_file(user_id, slug, 'README.md', _README_MD.format(slug=slug))

    persona_notes = req.persona_notes.strip() or _DEFAULT_PERSONA_NOTES.format(
        display_name=req.name, backstory=req.backstory or 'No backstory written yet.',
    )
    _write_agent_jsonc(user_id, slug, slug, req.goal, req.backstory, req.llm)
    _write_crew_jsonc(user_id, slug, slug)
    _write_output_schema(user_id, slug, True, _default_pydantic_fields())
    _write_skill_md(user_id, slug, slug, req.goal, persona_notes)

    return get_npc(user_id, slug)


def update_npc(user_id: str, slug: str, req: NpcUpdateRequest) -> NpcDetail:
    current = get_npc(user_id, slug)

    goal = req.goal if req.goal is not None else current.goal
    backstory = req.backstory if req.backstory is not None else current.backstory
    llm = req.llm if req.llm is not None else current.llm
    persona_notes = req.persona_notes if req.persona_notes is not None else current.persona_notes

    agent_name = _agent_name_for(user_id, slug)
    existing_skill_key = _skill_md_key(user_id, slug)
    skill_dir_name = existing_skill_key.rsplit('/', 2)[-2] if existing_skill_key else slug

    _write_agent_jsonc(user_id, slug, agent_name, goal, backstory, llm)
    _write_skill_md(user_id, slug, skill_dir_name, goal, persona_notes)
    # Rewritten unconditionally (not just on creation) so existing NPCs pick up template
    # fixes - e.g. the per-NPC memory wiring - the next time they're edited, instead of
    # being stuck forever with whatever npc.py existed when they were first created.
    _write_file(user_id, slug, 'npc.py', _NPC_PY)

    if req.pydantic_enabled is not None or req.pydantic_fields is not None:
        enabled = req.pydantic_enabled if req.pydantic_enabled is not None else current.pydantic_enabled
        fields = req.pydantic_fields if req.pydantic_fields is not None else current.pydantic_fields
        _write_output_schema(user_id, slug, enabled, fields)

    _prune_legacy_files(user_id, slug)

    # The execution cache (see ensure_cached) only ever syncs missing files, so without
    # clearing it here an already-cached NPC would keep serving whatever agent.jsonc/npc.py
    # it had at first talk, silently ignoring every edit made after that.
    cache_dir = _cache_dir(user_id, slug)
    if cache_dir.exists():
        shutil.rmtree(cache_dir)

    return get_npc(user_id, slug)


def _prune_legacy_files(user_id: str, slug: str) -> None:
    prefix = _npc_prefix(user_id, slug)
    cache_dir = _cache_dir(user_id, slug)
    for name in _LEGACY_FILES:
        key = prefix + name
        if storage.exists(_bucket(), key):
            storage.delete(_bucket(), key)
        local_path = cache_dir / name
        if local_path.exists():
            local_path.unlink()


def delete_npc(user_id: str, slug: str) -> None:
    prefix = _npc_prefix(user_id, slug)
    if not storage.exists(_bucket(), prefix + 'crew.jsonc'):
        raise NpcNotFoundError(slug)
    storage.delete_prefix(_bucket(), prefix)

    cache_dir = _cache_dir(user_id, slug)
    if cache_dir.exists():
        shutil.rmtree(cache_dir)


def ensure_cached(user_id: str, slug: str) -> Path:
    """Sync the NPC's files from storage into the local execution cache, if not already there.

    crewAI's loader needs real files on disk (it imports schemas.py and resolves the
    `skills` path relative to the project directory), so NPCs can't run directly out of
    storage - the cache is what `/talk` actually executes against.
    """
    cache_dir = _cache_dir(user_id, slug)
    if (cache_dir / 'crew.jsonc').exists():
        return cache_dir

    prefix = _npc_prefix(user_id, slug)
    keys = storage.list_files(_bucket(), prefix)
    if not keys:
        raise NpcNotFoundError(slug)

    for key in keys:
        rel = key[len(prefix):]
        if not rel or rel in _LEGACY_FILES:
            continue
        dest = cache_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if rel.startswith('memory/'):
            # LanceDB fragment files are binary - route them through the file-based
            # upload/download calls instead of the utf-8 text ones used for everything else.
            storage.download(_bucket(), key, str(dest))
        else:
            dest.write_text(storage.get_text(_bucket(), key), encoding='utf-8')

    return cache_dir


def sync_memory(user_id: str, slug: str) -> None:
    """Push an NPC's local LanceDB memory files up to storage after a conversation.

    crewAI's memory only ever writes to the local cache dir (see `ensure_cached`), so
    without this a fresh cache - a different instance, or this one after eviction - would
    come back with no memory of prior conversations.
    """
    cache_dir = _cache_dir(user_id, slug)
    memory_dir = cache_dir / 'memory'
    if not memory_dir.is_dir():
        return

    prefix = _npc_prefix(user_id, slug)
    for path in memory_dir.rglob('*'):
        if path.is_file():
            rel = path.relative_to(cache_dir).as_posix()
            storage.upload(_bucket(), prefix + rel, str(path))


def _write_file(user_id: str, slug: str, rel_path: str, content: str) -> None:
    local_path = _cache_dir(user_id, slug) / rel_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(content, encoding='utf-8')
    # normalize away '..' segments (e.g. rel_path='../__init__.py'): Supabase Storage's
    # Cloudflare front collapses '..' in the URL path before it reaches the S3-compatible
    # origin, which no longer matches the path boto3 signed -> SignatureDoesNotMatch.
    storage_key = posixpath.normpath(_npc_prefix(user_id, slug) + rel_path)
    storage.put_text(_bucket(), storage_key, content)


def _write_agent_jsonc(user_id: str, slug: str, agent_name: str, goal: str, backstory: str, llm: str) -> None:
    # crewai resolves relative "skills" paths against the process cwd instead
    # of the project directory (crewAIInc/crewAI#6585); core/ai/crewai_compat.py
    # patches this so the relative path below resolves correctly regardless of
    # where the process is launched from.
    agent = {
        'role': agent_name,
        'skills': ['./skills'],
        'goal': goal,
        'backstory': backstory,
        'llm': llm,
        # memory stays off here: agent-level memory=True resolves to crewAI's default
        # Memory(), which has no path override and falls back to a single global LanceDB
        # store shared by every agent on the machine - and agent.memory takes precedence
        # over crew._memory (see agent/core.py's `getattr(agent, "memory", None) or
        # self._memory`), so it would silently shadow the per-NPC-scoped crew.memory set
        # in npc.py and leak facts between unrelated NPCs.
        'settings': {'verbose': True, 'memory': False, 'cache': True},
    }
    content = '// Agent definition, generated by the NPC creator\n' + json.dumps(agent, indent=2) + '\n'
    _write_file(user_id, slug, f'agents/{agent_name}.jsonc', content)


def _write_crew_jsonc(user_id: str, slug: str, agent_name: str) -> None:
    crew = {
        'name': 'npc',
        'agents': [agent_name],
        'tasks': [{
            'name': 'conversation',
            'description': 'react to this prompt {prompt}',
            'expected_output': 'conversation',
            'output_pydantic': {'python': 'schemas.NpcResponseSchema'},
            'agent': agent_name,
        }],
        'process': 'sequential',
        'verbose': True,
        'memory': True,
        'stream': True,
        'inputs': {},
    }
    content = '// Crew definition, generated by the NPC creator\n' + json.dumps(crew, indent=2) + '\n'
    _write_file(user_id, slug, 'crew.jsonc', content)


def _write_skill_md(user_id: str, slug: str, skill_dir_name: str, goal: str, persona_notes: str) -> None:
    content = _SKILL_MD.format(slug=skill_dir_name, description=goal, persona_notes=persona_notes.strip())
    _write_file(user_id, slug, f'skills/{skill_dir_name}/SKILL.md', content)
