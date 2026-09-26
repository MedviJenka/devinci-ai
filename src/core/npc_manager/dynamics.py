from typing import Literal
from pydantic import BaseModel, Field


type Mood = Literal['Angry', 'Sad', 'Happy', 'Furious', 'Calm']


class DynamicMoodSchema(BaseModel):
    mood:        Mood  = Field(..., description='npc mood')
    trust_level: float = Field(..., description='npc trust_level', ge=0, le=100)


class DynamicMoodPage(): ...
