from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    owner_id: UUID
    jira_project_key: str | None = None
    created_at: datetime
    updated_at: datetime
    story_count: int = 0
    analysis_count: int = 0

    model_config = {"from_attributes": True}


class JiraProjectImport(BaseModel):
    """Request to create a space from a Jira project."""
    integration_id: UUID
    jira_project_key: str
    jira_project_name: str
