from pydantic import BaseModel, Field


class StoryCreationSchema(BaseModel):
    success:       bool = Field(default=False, description='Success/Fail')
    file_location: str  = Field(...,           description='File location')