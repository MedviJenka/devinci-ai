from pydantic import BaseModel, Field


class StoryCreationSchema(BaseModel):
    success:       bool = Field(default=False, description='Success/Fail')
    file_location: str  = Field(default='',    description='File location')
    description:   str  = Field(default='',    description='One-sentence NPC description')
    persona:       str  = Field(default='',    description='Full generated character profile')
    error:         str  = Field(default='',    description='Error message when success is False')