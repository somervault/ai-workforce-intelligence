from datetime import datetime

from pydantic import BaseModel


class JiraProjectDTO(BaseModel):
    id: str
    key: str
    name: str
    project_type: str | None = None


class JiraAccountDTO(BaseModel):
    account_id: str
    active: bool = True


class JiraIssueDTO(BaseModel):
    id: str
    key: str
    project_id: str
    project_key: str
    project_name: str
    summary: str
    status: str | None = None
    priority: str | None = None
    assignee_account_id: str | None = None
    assignee_display_name: str | None = None
    issue_type: str | None = None
    created: datetime | None = None
    updated: datetime | None = None
    resolution_date: datetime | None = None


class JiraChangelogItemDTO(BaseModel):
    field: str
    from_value: str | None = None
    to_value: str | None = None


class JiraIssueActivityDTO(BaseModel):
    id: str
    created: datetime | None = None
    author_account_id: str | None = None
    author_display_name: str | None = None
    items: list[JiraChangelogItemDTO]
