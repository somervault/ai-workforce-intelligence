import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmployeeProjectCreate(BaseModel):
    role: str = Field(min_length=1, max_length=100)


class EmployeeProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: uuid.UUID
    project_id: uuid.UUID
    role: str
    assigned_at: datetime
