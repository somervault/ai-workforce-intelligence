import uuid

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_project import EmployeeProject
from app.models.project import Project
from app.models.task import Task
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskPriority, TaskStatus, TaskUpdate

TASK_STATUSES = {"todo", "in_progress", "completed", "cancelled"}
TASK_PRIORITIES = {"low", "medium", "high", "critical"}


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = TaskRepository(db)

    def create_task(self, task_data: TaskCreate) -> Task:
        values = task_data.model_dump()
        self._validate_task_values(values)
        return self.repository.create(Task(**values))

    def get_task(self, task_id: uuid.UUID) -> Task | None:
        return self.repository.get_by_id(task_id)

    def get_tasks(self) -> list[Task]:
        return self.repository.get_all()

    def get_tasks_by_project(self, project_id: uuid.UUID) -> list[Task]:
        self._ensure_project_exists(project_id)
        return self.repository.get_by_project_id(project_id)

    def get_tasks_by_employee(self, employee_id: uuid.UUID) -> list[Task]:
        self._ensure_employee_exists(employee_id)
        return self.repository.get_by_assigned_employee_id(employee_id)

    def update_task(self, task_id: uuid.UUID, task_data: TaskUpdate) -> Task | None:
        task = self.repository.get_by_id(task_id)
        if task is None:
            return None

        values = task_data.model_dump(exclude_unset=True)
        effective_values = {
            "project_id": values.get("project_id", task.project_id),
            "assigned_employee_id": values.get(
                "assigned_employee_id", task.assigned_employee_id
            ),
            "status": values.get("status", task.status),
            "priority": values.get("priority", task.priority),
        }
        self._validate_task_values(effective_values)
        return self.repository.update(task, values)

    def delete_task(self, task_id: uuid.UUID) -> bool:
        task = self.repository.get_by_id(task_id)
        if task is None:
            return False
        self.repository.delete(task)
        return True

    def _validate_task_values(self, values: dict[str, object]) -> None:
        project_id = values["project_id"]
        assigned_employee_id = values.get("assigned_employee_id")
        status = values["status"]
        priority = values["priority"]

        if not isinstance(project_id, uuid.UUID):
            raise ValueError("project_id is required")
        self._ensure_project_exists(project_id)

        if status not in TASK_STATUSES:
            raise ValueError("Invalid task status")
        if priority not in TASK_PRIORITIES:
            raise ValueError("Invalid task priority")

        if assigned_employee_id is not None:
            if not isinstance(assigned_employee_id, uuid.UUID):
                raise ValueError("assigned_employee_id must be a UUID")
            self._ensure_employee_exists(assigned_employee_id)
            if self.db.get(EmployeeProject, (assigned_employee_id, project_id)) is None:
                raise ValueError("Assigned employee is not assigned to this project")

    def _ensure_project_exists(self, project_id: uuid.UUID) -> None:
        if self.db.get(Project, project_id) is None:
            raise LookupError("Project not found")

    def _ensure_employee_exists(self, employee_id: uuid.UUID) -> None:
        if self.db.get(Employee, employee_id) is None:
            raise LookupError("Employee not found")
