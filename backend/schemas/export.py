from uuid import UUID
from pydantic import BaseModel


class JiraExportRequest(BaseModel):
    jira_url: str | None = None
    project_key: str | None = None
    api_token: str | None = None
    email: str | None = None
    issue_type: str = "Task"
    integration_id: UUID | None = None


class ADOExportRequest(BaseModel):
    org_url: str | None = None
    project: str | None = None
    pat: str | None = None
    work_item_type: str = "Task"
    integration_id: UUID | None = None


class ServiceNowExportRequest(BaseModel):
    instance_url: str | None = None
    username: str | None = None
    password: str | None = None
    table: str = "rm_story"
    integration_id: UUID | None = None


class ExportResult(BaseModel):
    format: str
    items_exported: int
    message: str
    download_url: str | None = None
