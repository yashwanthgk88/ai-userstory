from pydantic import BaseModel


class JiraExportRequest(BaseModel):
    jira_url: str
    project_key: str
    api_token: str
    email: str
    issue_type: str = "Task"


class ADOExportRequest(BaseModel):
    org_url: str
    project: str
    pat: str
    work_item_type: str = "Task"


class ServiceNowExportRequest(BaseModel):
    instance_url: str
    username: str
    password: str
    table: str = "rm_story"


class ExportResult(BaseModel):
    format: str
    items_exported: int
    message: str
    download_url: str | None = None
