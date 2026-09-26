from datetime import datetime
from pydantic import BaseModel, Field


class ApiKeySummary(BaseModel):
    id: str
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class ApiKeyCreateResponse(ApiKeySummary):
    key: str = Field(..., description='raw key, shown only once at creation')
