from pydantic import BaseModel, Field
from typing import Literal


type Subscription = Literal['Free', 'Pro', 'Premium']


class UserSchema(BaseModel):
    id:           str          = Field(default=None)
    subscription: Subscription = Field(default='Free')
    api_calls:    int          = Field(default=0)
    characters:   int          = Field(default=0, le=5)
