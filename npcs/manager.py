import json
import re
from pathlib import Path
from typing import Any
from crewai.project import strip_jsonc_comments
from pydantic import BaseModel, Field

from core.settings import Config
from core.storage import client as storage


DEFAULT_LLM = 'openai/gpt-5.5'

_SCHEMAS_PY = '''from typing import Literal
from pydantic import BaseModel, Field


type Mood = Literal['Angry', 'Sad', 'Happy', 'Furious', 'Calm']


class NpcResponseSchema(BaseModel):
    mood:     Mood = Field(..., description='current npc mood based on the given prompt')
    response: str  = Field(..., description='npc response, rely also on memory')
'''

_NPC_PY = '''import asyncio
from pathlib import Path
import core.ai.crewai_compat  # noqa: F401
from crewai.project import load_crew
from crewai.types.streaming import CrewStreamingOutput


async def main(prompt: str) -> CrewStreamingOutput:
    crew, _ = load_crew(Path(__file__).with_name('crew.jsonc'))
    return await crew.kickoff_async(inputs={'prompt': prompt})


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


class NpcSummary(BaseModel):
    slug: str
    role: str
    goal: str
    llm: str


class NpcDetail(NpcSummary):
    backstory: str
    persona_notes: str


class NpcCreateRequest(BaseModel):
    name: str
    goal: str = Field(default='interactive npc')
    backstory: str = Field(default='')
    llm: str = Field(default=DEFAULT_LLM)
    persona_notes: str = Field(default='')


def slugify(name: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '_', name.strip().lower()).strip('_')
    if not slug:
        raise ValueError('name must contain at least one alphanumeric character')
    return slug


def _bucket() -> str:
    return Config.NPC_STORAGE_BUCKET


def _npc_prefix(user_id: str, slug: str) -> str:
    return f'{user_id}/{slug}/'


def _cache_dir(user_id: str, slug: str) -> Path:
    return Path(Config.NPC_CACHE_DIR) / user_id / slug


def _load_jsonc_text(text: str) -> Any:
    return json.loads(strip_jsonc_comments(text))


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


def get_npc(user_id: str, slug: str) -> NpcDetail:
    prefix = _npc_prefix(user_id, slug)
    if not storage.exists(_bucket(), prefix + 'crew.jsonc'):
        raise NpcNotFoundError(slug)

    agent_name = _agent_name_for(user_id, slug)
    agent = _load_jsonc_text(storage.get_text(_bucket(), prefix + f'agents/{agent_name}.jsonc'))

    skill_key = _skill_md_key(user_id, slug)
    persona_notes = _split_skill_md(storage.get_text(_bucket(), skill_key))[1] if skill_key else ''

    return NpcDetail(
        slug=slug,
        role=agent['role'],
        goal=agent['goal'],
        llm=agent['llm'],
        backstory=agent.get('backstory', ''),
        persona_notes=persona_notes,
    )


def create_npc(user_id: str, req: NpcCreateRequest) -> NpcDetail:
    slug = slugify(req.name)
    if storage.exists(_bucket(), _npc_prefix(user_id, slug) + 'crew.jsonc'):
        raise NpcAlreadyExistsError(slug)

    _write_file(user_id, slug, '__init__.py', '')
    _write_file(user_id, slug, 'npc.py', _NPC_PY)
    _write_file(user_id, slug, 'schemas.py', _SCHEMAS_PY)
    _write_file(user_id, slug, 'README.md', _README_MD.format(slug=slug))

    persona_notes = req.persona_notes.strip() or _DEFAULT_PERSONA_NOTES.format(
        display_name=req.name, backstory=req.backstory or 'No backstory written yet.',
    )
    _write_agent_jsonc(user_id, slug, slug, req.goal, req.backstory, req.llm)
    _write_crew_jsonc(user_id, slug, slug)
    _write_skill_md(user_id, slug, slug, req.goal, persona_notes)

    return get_npc(user_id, slug)


def _write_file(user_id: str, slug: str, rel_path: str, content: str) -> None:
    local_path = _cache_dir(user_id, slug) / rel_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(content, encoding='utf-8')
    storage.put_text(_bucket(), _npc_prefix(user_id, slug) + rel_path, content)


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
        'settings': {'verbose': True, 'memory': True, 'cache': True},
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
