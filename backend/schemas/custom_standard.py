from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class CustomStandardControl(BaseModel):
    control_id: str
    title: str
    description: str
    category: str | None = None


class CustomStandardResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    description: str | None
    file_type: str | None
    original_filename: str | None
    controls: list[CustomStandardControl]
    uploaded_at: datetime

    model_config = {"from_attributes": True}
