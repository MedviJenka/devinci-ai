from pathlib import Path
from typing import Any, Literal
from crewai import Agent, Memory
from pydantic import BaseModel, Field, create_model
from .schemas import NpcDetail, PydanticFieldDef, _FIELD_TYPES


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
