import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee_project import EmployeeProject


class EmployeeProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def assign(
        self, employee_id: uuid.UUID, project_id: uuid.UUID, role: str
    ) -> EmployeeProject:
        assignment = EmployeeProject(
            employee_id=employee_id,
            project_id=project_id,
            role=role,
        )
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def get_assignment(
        self, employee_id: uuid.UUID, project_id: uuid.UUID
    ) -> EmployeeProject | None:
        return self.db.get(EmployeeProject, (employee_id, project_id))

    def get_by_project_id(self, project_id: uuid.UUID) -> list[EmployeeProject]:
        statement = select(EmployeeProject).where(EmployeeProject.project_id == project_id)
        return list(self.db.scalars(statement.order_by(EmployeeProject.assigned_at)))

    def get_by_employee_id(self, employee_id: uuid.UUID) -> list[EmployeeProject]:
        statement = select(EmployeeProject).where(EmployeeProject.employee_id == employee_id)
        return list(self.db.scalars(statement.order_by(EmployeeProject.assigned_at)))

    def remove(self, assignment: EmployeeProject) -> None:
        self.db.delete(assignment)
        self.db.commit()
