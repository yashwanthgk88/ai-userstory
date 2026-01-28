from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class WebhookCreate(BaseModel):
    url: str
    event_types: list[str]  # analysis.completed, analysis.failed, bulk_analysis.completed
    secret: str


class WebhookResponse(BaseModel):
    id: UUID
    project_id: UUID
    url: str
    event_types: list[str]
    is_active: bool
    created_at: datetime
    last_triggered_at: datetime | None

    model_config = {"from_attributes": True}
