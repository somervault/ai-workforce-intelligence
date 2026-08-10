import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


class EmployeeConflictError(Exception):
    pass


class EmployeeService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = EmployeeRepository(db)

    def create_employee(self, employee_data: EmployeeCreate) -> Employee:
        self._ensure_department_exists(employee_data.department_id)
        self._ensure_unique_fields(employee_data.employee_code, employee_data.email)

        employee = Employee(**employee_data.model_dump())
        try:
            return self.repository.create(employee)
        except IntegrityError as error:
            self.db.rollback()
            raise EmployeeConflictError("Employee code or email already exists") from error

    def get_employee(self, employee_id: uuid.UUID) -> Employee | None:
        return self.repository.get_by_id(employee_id)

    def get_employees(self) -> list[Employee]:
        return self.repository.get_all()

    def update_employee(
        self, employee_id: uuid.UUID, employee_data: EmployeeUpdate
    ) -> Employee | None:
        employee = self.repository.get_by_id(employee_id)
        if employee is None:
            return None

        values = employee_data.model_dump(exclude_unset=True)
        if "department_id" in values:
            self._ensure_department_exists(values["department_id"])

        self._ensure_unique_fields(
            values.get("employee_code"),
            values.get("email"),
            exclude_employee_id=employee_id,
        )
        try:
            return self.repository.update(employee, values)
        except IntegrityError as error:
            self.db.rollback()
            raise EmployeeConflictError("Employee code or email already exists") from error

    def delete_employee(self, employee_id: uuid.UUID) -> bool:
        employee = self.repository.get_by_id(employee_id)
        if employee is None:
            return False
        self.repository.delete(employee)
        return True

    def _ensure_department_exists(self, department_id: uuid.UUID) -> None:
        if self.db.get(Department, department_id) is None:
            raise ValueError("Department not found")

    def _ensure_unique_fields(
        self,
        employee_code: str | None,
        email: str | None,
        exclude_employee_id: uuid.UUID | None = None,
    ) -> None:
        if employee_code:
            employee = self.repository.get_by_employee_code(employee_code)
            if employee and employee.id != exclude_employee_id:
                raise EmployeeConflictError("Employee code already exists")
        if email:
            employee = self.repository.get_by_email(email)
            if employee and employee.id != exclude_employee_id:
                raise EmployeeConflictError("Employee email already exists")
