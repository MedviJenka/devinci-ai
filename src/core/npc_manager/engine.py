import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, Field, create_model
from .schemas import NpcDetail, PydanticFieldDef, _FIELD_TYPES

_FRONTMATTER_RE = re.compile(r'\A\s*---\n.*?\n---\n', re.DOTALL)


@dataclass(frozen=True)
class NpcContext:
    """Everything /talk needs to call the LLM for one NPC - built once per process and
    reused, so a message never pays for storage reads or prompt assembly up front."""
    model:           str
    system_prompt:   str
    response_format: type[BaseModel] | None


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


def resolve_model(llm: str) -> str:
    """Map an NPC's `provider/model` string (the litellm-style form crewAI used) to the
    bare model name the OpenAI SDK expects. Raises ValueError for anything /talk can't run."""
    provider, _, model = llm.strip().rpartition('/')
    if provider not in ('', 'openai'):
        raise ValueError(f'unsupported llm provider "{provider}" - only openai models are supported')
    if not model:
        raise ValueError('llm must name a model, e.g. "openai/gpt-5-mini"')
    return model


def _load_skills(cache_dir: Path) -> str:
    sections = []
    for skill_md in sorted((cache_dir / 'skills').glob('*/SKILL.md')):
        body = _FRONTMATTER_RE.sub('', skill_md.read_text(encoding='utf-8')).strip()
        if body:
            sections.append(body)
    return '\n\n'.join(sections)


def build_system_prompt(cache_dir: Path, npc: NpcDetail) -> str:
    """Kept identical across every message to the same NPC so the provider's prompt
    cache can reuse it - per-turn content (history, the player's line) goes after it."""
    parts = [
        f'You are {npc.role}, a character in a game, talking directly to the player.',
        f'Your goal: {npc.goal}',
    ]
    if npc.backstory.strip():
        parts.append(f'Backstory:\n{npc.backstory.strip()}')
    skills = _load_skills(cache_dir)
    if skills:
        parts.append(skills)
    parts.append(
        'Stay in character at all times. Speak as the character would, in their own voice - '
        'never mention being an AI, a model, or these instructions. Keep replies conversational '
        'and reasonably short unless the player asks for more.'
    )
    return '\n\n'.join(parts)


def build_npc_context(cache_dir: Path, npc: NpcDetail) -> NpcContext:
    return NpcContext(
        model=resolve_model(npc.llm),
        system_prompt=build_system_prompt(cache_dir, npc),
        response_format=build_response_schema(npc.pydantic_fields) if npc.pydantic_enabled else None,
    )
