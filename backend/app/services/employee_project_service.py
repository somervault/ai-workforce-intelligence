import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_project import EmployeeProject
from app.models.project import Project
from app.repositories.employee_project_repository import EmployeeProjectRepository
from app.schemas.employee_project import EmployeeProjectCreate


class EmployeeProjectConflictError(Exception):
    pass


class EmployeeProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = EmployeeProjectRepository(db)

    def assign_employee(
        self,
        project_id: uuid.UUID,
        employee_id: uuid.UUID,
        assignment_data: EmployeeProjectCreate,
    ) -> EmployeeProject:
        self._ensure_project_exists(project_id)
        self._ensure_employee_exists(employee_id)
        if self.repository.get_assignment(employee_id, project_id) is not None:
            raise EmployeeProjectConflictError("Employee is already assigned to this project")
        try:
            return self.repository.assign(employee_id, project_id, assignment_data.role)
        except IntegrityError as error:
            self.db.rollback()
            raise EmployeeProjectConflictError(
                "Employee is already assigned to this project"
            ) from error

    def get_project_assignments(self, project_id: uuid.UUID) -> list[EmployeeProject]:
        self._ensure_project_exists(project_id)
        return self.repository.get_by_project_id(project_id)

    def get_employee_assignments(self, employee_id: uuid.UUID) -> list[EmployeeProject]:
        self._ensure_employee_exists(employee_id)
        return self.repository.get_by_employee_id(employee_id)

    def remove_employee(self, project_id: uuid.UUID, employee_id: uuid.UUID) -> bool:
        self._ensure_project_exists(project_id)
        self._ensure_employee_exists(employee_id)
        assignment = self.repository.get_assignment(employee_id, project_id)
        if assignment is None:
            return False
        self.repository.remove(assignment)
        return True

    def _ensure_employee_exists(self, employee_id: uuid.UUID) -> None:
        if self.db.get(Employee, employee_id) is None:
            raise ValueError("Employee not found")

    def _ensure_project_exists(self, project_id: uuid.UUID) -> None:
        if self.db.get(Project, project_id) is None:
            raise ValueError("Project not found")
