from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class IntegrationCreate(BaseModel):
    integration_type: str  # jira, ado, servicenow
    name: str
    config: dict  # url, project_key, email, etc.
    token: str  # api_token / pat / password


class GlobalIntegrationCreate(BaseModel):
    """Create a global (user-level) integration not tied to any project."""
    integration_type: str  # jira, ado, servicenow
    name: str
    config: dict  # url, email, etc.
    token: str  # api_token / pat / password


class IntegrationResponse(BaseModel):
    id: UUID
    project_id: UUID | None  # Nullable for global integrations
    integration_type: str
    name: str
    config: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class IntegrationUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None
    token: str | None = None


class JiraProjectResponse(BaseModel):
    """Response for a Jira project."""
    id: str
    key: str
    name: str
    avatar_url: str | None = None
