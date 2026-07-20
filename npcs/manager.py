import json
import re
import shutil
from pathlib import Path
from typing import Any
from crewai.project import strip_jsonc_comments
from pydantic import BaseModel, Field


NPCS_DIR = Path(__file__).parent

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


class NpcUpdateRequest(BaseModel):
    goal: str | None = None
    backstory: str | None = None
    llm: str | None = None
    persona_notes: str | None = None


def slugify(name: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '_', name.strip().lower()).strip('_')
    if not slug:
        raise ValueError('name must contain at least one alphanumeric character')
    return slug


def _npc_dir(slug: str) -> Path:
    return NPCS_DIR / slug


def _load_jsonc(path: Path) -> Any:
    return json.loads(strip_jsonc_comments(path.read_text(encoding='utf-8')))


def _agent_name_for(npc_dir: Path) -> str:
    crew = _load_jsonc(npc_dir / 'crew.jsonc')
    return crew['agents'][0]


def _skill_md_path(npc_dir: Path) -> Path | None:
    skills_dir = npc_dir / 'skills'
    if not skills_dir.is_dir():
        return None
    return next(skills_dir.glob('*/SKILL.md'), None)


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


def list_npcs() -> list[NpcSummary]:
    summaries = []
    for npc_dir in sorted(NPCS_DIR.iterdir()):
        if npc_dir.name.startswith('_') or not (npc_dir / 'crew.jsonc').exists():
            continue
        try:
            summaries.append(_read_summary(npc_dir))
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            continue
    return summaries


def _read_summary(npc_dir: Path) -> NpcSummary:
    agent_name = _agent_name_for(npc_dir)
    agent = _load_jsonc(npc_dir / 'agents' / f'{agent_name}.jsonc')
    return NpcSummary(slug=npc_dir.name, role=agent['role'], goal=agent['goal'], llm=agent['llm'])


def get_npc(slug: str) -> NpcDetail:
    npc_dir = _npc_dir(slug)
    if not npc_dir.is_dir():
        raise NpcNotFoundError(slug)

    agent_name = _agent_name_for(npc_dir)
    agent = _load_jsonc(npc_dir / 'agents' / f'{agent_name}.jsonc')

    skill_path = _skill_md_path(npc_dir)
    persona_notes = _split_skill_md(skill_path.read_text(encoding='utf-8'))[1] if skill_path else ''

    return NpcDetail(
        slug=slug,
        role=agent['role'],
        goal=agent['goal'],
        llm=agent['llm'],
        backstory=agent.get('backstory', ''),
        persona_notes=persona_notes,
    )


def create_npc(req: NpcCreateRequest) -> NpcDetail:
    slug = slugify(req.name)
    npc_dir = _npc_dir(slug)
    if npc_dir.exists():
        raise NpcAlreadyExistsError(slug)

    (npc_dir / 'agents').mkdir(parents=True)
    (npc_dir / 'skills' / slug).mkdir(parents=True)

    (npc_dir / '__init__.py').write_text('', encoding='utf-8')
    (npc_dir / 'npc.py').write_text(_NPC_PY, encoding='utf-8')
    (npc_dir / 'schemas.py').write_text(_SCHEMAS_PY, encoding='utf-8')
    (npc_dir / 'README.md').write_text(_README_MD.format(slug=slug), encoding='utf-8')

    persona_notes = req.persona_notes.strip() or _DEFAULT_PERSONA_NOTES.format(
        display_name=req.name, backstory=req.backstory or 'No backstory written yet.',
    )
    _write_agent_jsonc(npc_dir, slug, req.goal, req.backstory, req.llm)
    _write_crew_jsonc(npc_dir, slug)
    _write_skill_md(npc_dir, slug, req.goal, persona_notes)

    return get_npc(slug)


def update_npc(slug: str, req: NpcUpdateRequest) -> NpcDetail:
    current = get_npc(slug)
    npc_dir = _npc_dir(slug)

    goal = req.goal if req.goal is not None else current.goal
    backstory = req.backstory if req.backstory is not None else current.backstory
    llm = req.llm if req.llm is not None else current.llm
    persona_notes = req.persona_notes if req.persona_notes is not None else current.persona_notes

    agent_name = _agent_name_for(npc_dir)
    existing_skill_path = _skill_md_path(npc_dir)
    skill_dir_name = existing_skill_path.parent.name if existing_skill_path else slug

    _write_agent_jsonc(npc_dir, agent_name, goal, backstory, llm)
    _write_skill_md(npc_dir, skill_dir_name, goal, persona_notes)

    return get_npc(slug)


def delete_npc(slug: str) -> None:
    npc_dir = _npc_dir(slug)
    if not npc_dir.is_dir():
        raise NpcNotFoundError(slug)
    shutil.rmtree(npc_dir)


def _write_agent_jsonc(npc_dir: Path, agent_name: str, goal: str, backstory: str, llm: str) -> None:
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
    (npc_dir / 'agents' / f'{agent_name}.jsonc').write_text(content, encoding='utf-8')


def _write_crew_jsonc(npc_dir: Path, agent_name: str) -> None:
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
    (npc_dir / 'crew.jsonc').write_text(content, encoding='utf-8')


def _write_skill_md(npc_dir: Path, slug: str, goal: str, persona_notes: str) -> None:
    content = _SKILL_MD.format(slug=slug, description=goal, persona_notes=persona_notes.strip())
    (npc_dir / 'skills' / slug / 'SKILL.md').write_text(content, encoding='utf-8')
