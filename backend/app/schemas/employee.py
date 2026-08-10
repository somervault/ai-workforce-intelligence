import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmployeeFields(BaseModel):
    @field_validator("email", check_fields=False)
    @classmethod
    def validate_email(cls, value: str) -> str:
        local_part, separator, domain = value.partition("@")
        if not local_part or not separator or "." not in domain:
            raise ValueError("email must be a valid email address")
        return value


class EmployeeCreate(EmployeeFields):
    employee_code: str = Field(min_length=1, max_length=20)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    designation: str = Field(min_length=1, max_length=100)
    department_id: uuid.UUID


class EmployeeUpdate(EmployeeFields):
    employee_code: str | None = Field(default=None, min_length=1, max_length=20)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    designation: str | None = Field(default=None, min_length=1, max_length=100)
    department_id: uuid.UUID | None = None


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_code: str
    first_name: str
    last_name: str
    email: str
    designation: str
    department_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
