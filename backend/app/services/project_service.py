import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, db: Session):
        self.repository = ProjectRepository(db)

    def create_project(self, project_data: ProjectCreate) -> Project:
        return self.repository.create(Project(**project_data.model_dump()))

    def get_project(self, project_id: uuid.UUID) -> Project | None:
        return self.repository.get_by_id(project_id)

    def get_projects(self) -> list[Project]:
        return self.repository.get_all()

    def update_project(
        self, project_id: uuid.UUID, project_data: ProjectUpdate
    ) -> Project | None:
        project = self.repository.get_by_id(project_id)
        if project is None:
            return None

        values = project_data.model_dump(exclude_unset=True)
        self._validate_updated_date_range(project, values)
        return self.repository.update(project, values)

    def delete_project(self, project_id: uuid.UUID) -> bool:
        project = self.repository.get_by_id(project_id)
        if project is None:
            return False
        self.repository.delete(project)
        return True

    @staticmethod
    def _validate_updated_date_range(project: Project, values: dict[str, object]) -> None:
        start_date = values.get("start_date", project.start_date)
        end_date = values.get("end_date", project.end_date)
        if isinstance(start_date, date) and isinstance(end_date, date) and end_date < start_date:
            raise ValueError("end_date cannot be before start_date")
