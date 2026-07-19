from typing import Literal
from pydantic import BaseModel, Field


type Mood = Literal['Angry', 'Sad', 'Happy', 'Furious', 'Calm']


class NpcResponseSchema(BaseModel):
    mood:     Mood = Field(..., description='current npc mood based on the given prompt')
    response: str  = Field(..., description='npc response, rely also on memory')
