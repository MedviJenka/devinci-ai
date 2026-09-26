from typing import Literal, Optional
from pydantic import BaseModel, Field
from core.settings import Config
from core.voice.schemas import SupportedTone


_FIELD_TYPES: dict[str, type] = {'string': str, 'integer': int, 'float': float, 'boolean': bool}


class PydanticFieldDef(BaseModel):
    name:        str
    type:        Literal['string', 'integer', 'float', 'boolean', 'enum']
    description: str       = ''
    enum_values: list[str] = Field(default_factory=list)
    required:    bool      = True


def _default_pydantic_fields() -> list[PydanticFieldDef]:
    return [
        PydanticFieldDef(
            name='mood', type='enum', description='current npc mood based on the given prompt',
            enum_values=['Angry', 'Sad', 'Happy', 'Furious', 'Calm'], required=True,
        ),
        PydanticFieldDef(
            name='attitude', type='enum',
            description="the npc's interpersonal stance toward the player right now, driven by mood and conversation history",
            enum_values=['Friendly', 'Warm', 'Guarded', 'Dismissive', 'Hostile', 'Playful'], required=True,
        ),
        PydanticFieldDef(
            name='tone', type='enum',
            description='vocal delivery for this line - how it should sound spoken aloud, matching the mood and attitude above',
            enum_values=[tone.value for tone in SupportedTone], required=True,
        ),
        PydanticFieldDef(name='response', type='string', description='npc response, rely also on memory', required=True),
    ]


class NpcSummary(BaseModel):
    slug: str
    role: str
    goal: str
    llm:  str


class NpcDetail(NpcSummary):
    backstory:        str
    persona_notes:    str
    pydantic_enabled: bool
    pydantic_fields:  list[PydanticFieldDef]


class NpcCreateRequest(BaseModel):
    name:          str
    goal:          str = Field(default='interactive npc')
    backstory:     str = Field(default='')
    llm:           str = Field(default=Config.OPENAI_MODEL)
    persona_notes: str = Field(default='')


class NpcUpdateRequest(BaseModel):
    goal:             Optional[str]                    = None
    backstory:        Optional[str]                    = None
    llm:              Optional[str]                    = None
    persona_notes:    Optional[str]                    = None
    pydantic_enabled: Optional[bool]                   = None
    pydantic_fields:  Optional[list[PydanticFieldDef]] = None
