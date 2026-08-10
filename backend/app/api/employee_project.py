import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.employee_project import EmployeeProjectCreate, EmployeeProjectResponse
from app.services.employee_project_service import (
    EmployeeProjectConflictError,
    EmployeeProjectService,
)

router = APIRouter(tags=["employee-projects"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/projects/{project_id}/employees/{employee_id}",
    response_model=EmployeeProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_employee_to_project(
    project_id: uuid.UUID,
    employee_id: uuid.UUID,
    assignment_data: EmployeeProjectCreate,
    db: DbSession,
) -> EmployeeProjectResponse:
    try:
        return EmployeeProjectService(db).assign_employee(
            project_id, employee_id, assignment_data
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except EmployeeProjectConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get(
    "/projects/{project_id}/employees", response_model=list[EmployeeProjectResponse]
)
def get_project_employees(
    project_id: uuid.UUID, db: DbSession
) -> list[EmployeeProjectResponse]:
    try:
        return EmployeeProjectService(db).get_project_assignments(project_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get(
    "/employees/{employee_id}/projects", response_model=list[EmployeeProjectResponse]
)
def get_employee_projects(
    employee_id: uuid.UUID, db: DbSession
) -> list[EmployeeProjectResponse]:
    try:
        return EmployeeProjectService(db).get_employee_assignments(employee_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.delete(
    "/projects/{project_id}/employees/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_employee_from_project(
    project_id: uuid.UUID, employee_id: uuid.UUID, db: DbSession
) -> None:
    try:
        removed = EmployeeProjectService(db).remove_employee(project_id, employee_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
