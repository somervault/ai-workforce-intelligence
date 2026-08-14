import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

SCORING_VERSION = "workforce-v1"


class WorkforceAnalysisConfiguration(BaseModel):
    window_days: int = Field(default=30, ge=1)
    due_soon_days: int = Field(default=7, ge=0)
    open_task_weight: float = Field(default=45, ge=0)
    due_date_weight: float = Field(default=25, ge=0)
    active_project_weight: float = Field(default=20, ge=0)
    completion_relief_weight: float = Field(default=10, ge=0)
    internal_activity_weight: float = Field(default=35, ge=0)
    jira_activity_weight: float = Field(default=30, ge=0)
    github_activity_weight: float = Field(default=35, ge=0)
    underloaded_threshold: float = Field(default=35, ge=0, le=100)
    overloaded_threshold: float = Field(default=70, ge=0, le=100)
    external_max_results: int = Field(default=25, ge=1, le=100)

    @model_validator(mode="after")
    def validate_configuration(self) -> "WorkforceAnalysisConfiguration":
        if self.underloaded_threshold >= self.overloaded_threshold:
            raise ValueError("underloaded threshold must be below overloaded threshold")
        if self.open_task_weight + self.due_date_weight + self.active_project_weight != 90:
            raise ValueError("workload pressure weights must total 90")
        if self.internal_activity_weight + self.jira_activity_weight + self.github_activity_weight != 100:
            raise ValueError("activity weights must total 100")
        return self


class EmployeeIdentityDTO(BaseModel):
    id: uuid.UUID
    employee_code: str
    first_name: str
    last_name: str
    designation: str


class WorkforceRawCountsDTO(BaseModel):
    assigned_open_tasks: int
    priority_weight_total: int
    overdue_tasks: int
    due_soon_tasks: int
    active_project_assignments: int
    completed_tasks_in_window: int
    internal_task_events_in_window: int
    jira_activity_events: int = 0
    github_activity_events: int = 0


class WorkforceComponentScoresDTO(BaseModel):
    open_task_score: float
    due_date_pressure_score: float
    active_project_load_score: float
    completion_relief_score: float
    internal_task_activity_score: float
    jira_activity_score: float = 0
    github_activity_score: float = 0


class EmployeeWorkforceAnalysisDTO(BaseModel):
    employee: EmployeeIdentityDTO
    workload_score: float
    activity_score: float
    classification: Literal["underloaded", "balanced", "overloaded"]
    component_scores: WorkforceComponentScoresDTO
    raw_counts: WorkforceRawCountsDTO
    factors: list[str]
    scoring_version: str = SCORING_VERSION


class UnattributedExternalActivityDTO(BaseModel):
    jira_issue_count: int
    jira_activity_score: float
    github_commit_count: int
    github_pull_request_count: int
    github_review_count: int
    github_activity_score: float
    unavailable_sources: list[str]
    factors: list[str]


class WorkforceAnalysisResultDTO(BaseModel):
    generated_at: datetime
    analysis_start_date: date
    configuration: WorkforceAnalysisConfiguration
    employees: list[EmployeeWorkforceAnalysisDTO]
    unattributed_external_activity: UnattributedExternalActivityDTO
    scoring_version: str = SCORING_VERSION
