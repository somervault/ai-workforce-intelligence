import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TaskStatus = Literal["todo", "in_progress", "completed", "cancelled"]
TaskPriority = Literal["low", "medium", "high", "critical"]


class TaskCreate(BaseModel):
    project_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus
    priority: TaskPriority
    assigned_employee_id: uuid.UUID | None = None
    due_date: date | None = None


class TaskUpdate(BaseModel):
    project_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assigned_employee_id: uuid.UUID | None = None
    due_date: date | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assigned_employee_id: uuid.UUID | None
    due_date: date | None
    created_at: datetime
    updated_at: datetime
