import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

IdentityProvider = Literal["jira", "github"]
IdentityStatus = Literal["active", "inactive", "deleted"]


class EmployeeExternalIdentityCreate(BaseModel):
    provider: IdentityProvider
    external_id: str = Field(min_length=1, max_length=255)


class EmployeeExternalIdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    provider: IdentityProvider
    external_id: str
    external_login: str | None
    status: IdentityStatus
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime
