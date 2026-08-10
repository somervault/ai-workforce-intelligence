import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task


class TaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, task: Task) -> Task:
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        return self.db.get(Task, task_id)

    def get_all(self) -> list[Task]:
        return list(self.db.scalars(select(Task).order_by(Task.created_at)))

    def get_by_project_id(self, project_id: uuid.UUID) -> list[Task]:
        statement = select(Task).where(Task.project_id == project_id)
        return list(self.db.scalars(statement.order_by(Task.created_at)))

    def get_by_assigned_employee_id(self, employee_id: uuid.UUID) -> list[Task]:
        statement = select(Task).where(Task.assigned_employee_id == employee_id)
        return list(self.db.scalars(statement.order_by(Task.created_at)))

    def update(self, task: Task, values: dict[str, object]) -> Task:
        for field, value in values.items():
            setattr(task, field, value)
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete(self, task: Task) -> None:
        self.db.delete(task)
        self.db.commit()
