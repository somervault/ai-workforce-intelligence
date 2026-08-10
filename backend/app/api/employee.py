import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.employee import EmployeeCreate, EmployeeResponse, EmployeeUpdate
from app.services.employee_service import EmployeeConflictError, EmployeeService

router = APIRouter(prefix="/employees", tags=["employees"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(employee_data: EmployeeCreate, db: DbSession) -> EmployeeResponse:
    service = EmployeeService(db)
    try:
        return service.create_employee(employee_data)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except EmployeeConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("", response_model=list[EmployeeResponse])
def get_employees(db: DbSession) -> list[EmployeeResponse]:
    return EmployeeService(db).get_employees()


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(employee_id: uuid.UUID, db: DbSession) -> EmployeeResponse:
    employee = EmployeeService(db).get_employee(employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: uuid.UUID, employee_data: EmployeeUpdate, db: DbSession
) -> EmployeeResponse:
    service = EmployeeService(db)
    try:
        employee = service.update_employee(employee_id, employee_data)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except EmployeeConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(employee_id: uuid.UUID, db: DbSession) -> None:
    if not EmployeeService(db).delete_employee(employee_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
