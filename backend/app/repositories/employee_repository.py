import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee


class EmployeeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, employee: Employee) -> Employee:
        self.db.add(employee)
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def get_by_id(self, employee_id: uuid.UUID) -> Employee | None:
        return self.db.get(Employee, employee_id)

    def get_all(self) -> list[Employee]:
        return list(self.db.scalars(select(Employee).order_by(Employee.created_at)))

    def get_by_employee_code(self, employee_code: str) -> Employee | None:
        statement = select(Employee).where(Employee.employee_code == employee_code)
        return self.db.scalar(statement)

    def get_by_email(self, email: str) -> Employee | None:
        statement = select(Employee).where(Employee.email == email)
        return self.db.scalar(statement)

    def update(self, employee: Employee, values: dict[str, object]) -> Employee:
        for field, value in values.items():
            setattr(employee, field, value)
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def delete(self, employee: Employee) -> None:
        self.db.delete(employee)
        self.db.commit()
