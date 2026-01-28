from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class StoryCreate(BaseModel):
    title: str
    description: str
    acceptance_criteria: str | None = None


class StoryResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str
    acceptance_criteria: str | None
    source: str
    external_id: str | None
    external_url: str | None
    created_at: datetime
    analysis_count: int = 0

    model_config = {"from_attributes": True}


class JiraImportRequest(BaseModel):
    jira_url: str | None = None
    project_key: str | None = None
    api_token: str | None = None
    email: str | None = None
    jql: str | None = None
    integration_id: UUID | None = None


class ADOImportRequest(BaseModel):
    org_url: str | None = None
    project: str | None = None
    pat: str | None = None
    query: str | None = None
    integration_id: UUID | None = None
