import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.employee_external_identity import EmployeeExternalIdentityCreate, EmployeeExternalIdentityResponse
from app.services.employee_external_identity_service import (
    EmployeeExternalIdentityConflictError,
    EmployeeExternalIdentityService,
    EmployeeExternalIdentityVerificationError,
)

router = APIRouter(tags=["employee-external-identities"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/employees/{employee_id}/external-identities", response_model=EmployeeExternalIdentityResponse, status_code=status.HTTP_201_CREATED)
def create_external_identity(employee_id: uuid.UUID, data: EmployeeExternalIdentityCreate, db: DbSession) -> EmployeeExternalIdentityResponse:
    try:
        return EmployeeExternalIdentityService(db).create_mapping(employee_id, data)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except EmployeeExternalIdentityConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except EmployeeExternalIdentityVerificationError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/employees/{employee_id}/external-identities", response_model=list[EmployeeExternalIdentityResponse])
def get_employee_external_identities(employee_id: uuid.UUID, db: DbSession) -> list[EmployeeExternalIdentityResponse]:
    try:
        return EmployeeExternalIdentityService(db).get_employee_mappings(employee_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/external-identities/{mapping_id}", response_model=EmployeeExternalIdentityResponse)
def get_external_identity(mapping_id: uuid.UUID, db: DbSession) -> EmployeeExternalIdentityResponse:
    mapping = EmployeeExternalIdentityService(db).get_mapping(mapping_id)
    if mapping is None:
        raise HTTPException(status_code=404, detail="External identity mapping not found")
    return mapping


@router.post("/external-identities/{mapping_id}/verify", response_model=EmployeeExternalIdentityResponse)
def verify_external_identity(mapping_id: uuid.UUID, db: DbSession) -> EmployeeExternalIdentityResponse:
    try:
        mapping = EmployeeExternalIdentityService(db).verify_mapping(mapping_id)
    except EmployeeExternalIdentityVerificationError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    if mapping is None:
        raise HTTPException(status_code=404, detail="External identity mapping not found")
    return mapping


@router.delete("/external-identities/{mapping_id}", response_model=EmployeeExternalIdentityResponse)
def deactivate_external_identity(mapping_id: uuid.UUID, db: DbSession) -> EmployeeExternalIdentityResponse:
    mapping = EmployeeExternalIdentityService(db).deactivate_mapping(mapping_id)
    if mapping is None:
        raise HTTPException(status_code=404, detail="External identity mapping not found")
    return mapping
