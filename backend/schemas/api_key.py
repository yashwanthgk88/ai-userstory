from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class APIKeyCreate(BaseModel):
    name: str


class APIKeyResponse(BaseModel):
    id: UUID
    name: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class APIKeyCreated(APIKeyResponse):
    key: str  # raw key, shown only once
