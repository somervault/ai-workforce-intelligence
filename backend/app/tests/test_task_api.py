import unittest
import uuid
from datetime import date

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.task import (
    create_task,
    delete_task,
    get_employee_tasks,
    get_project_tasks,
    get_task,
    get_tasks,
    update_task,
)
from app.database.base import Base
from app.models.department import Department
from app.models.employee import Employee
from app.models.employee_project import EmployeeProject
from app.models.project import Project
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


class TestTaskAPI(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.drop_all(bind=test_engine)
        Base.metadata.create_all(bind=test_engine)
        self.db: Session = TestSessionLocal()

        department = Department(name="Engineering")
        self.employee = Employee(
            employee_code="EMP-001",
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            designation="Engineer",
            department=department,
        )
        self.unassigned_employee = Employee(
            employee_code="EMP-002",
            first_name="Grace",
            last_name="Hopper",
            email="grace@example.com",
            designation="Engineer",
            department=department,
        )
        self.project = Project(name="Platform upgrade", status="planned")
        self.other_project = Project(name="Data migration", status="active")
        self.db.add_all(
            [self.employee, self.unassigned_employee, self.project, self.other_project]
        )
        self.db.commit()
        self.db.add(
            EmployeeProject(
                employee_id=self.employee.id,
                project_id=self.project.id,
                role="Developer",
            )
        )
        self.db.commit()
        self.db.refresh(self.employee)
        self.db.refresh(self.project)

    def tearDown(self) -> None:
        self.db.close()

    def task_data(
        self,
        project_id: uuid.UUID | None = None,
        employee_id: uuid.UUID | None = None,
    ) -> TaskCreate:
        return TaskCreate(
            project_id=project_id or self.project.id,
            title="Build project dashboard",
            description="Show project progress.",
            status="todo",
            priority="high",
            assigned_employee_id=employee_id,
            due_date=date(2026, 9, 1),
        )

    def test_task_creation_retrieval_update_and_deletion(self) -> None:
        created = create_task(
            self.task_data(employee_id=self.employee.id), self.db
        )
        assert created.title == "Build project dashboard"
        assert len(get_tasks(self.db)) == 1
        assert get_task(created.id, self.db).id == created.id

        updated = update_task(
            created.id,
            TaskUpdate(status="in_progress", priority="critical"),
            self.db,
        )
        assert updated.status == "in_progress"
        assert updated.priority == "critical"

        assert delete_task(created.id, self.db) is None
        with self.assertRaises(HTTPException) as error:
            get_task(created.id, self.db)
        assert error.exception.status_code == 404

    def test_task_filters(self) -> None:
        assigned_task = create_task(
            self.task_data(employee_id=self.employee.id), self.db
        )
        unassigned_task = create_task(
            self.task_data(), self.db
        )

        project_tasks = get_project_tasks(self.project.id, self.db)
        assert {task.id for task in project_tasks} == {assigned_task.id, unassigned_task.id}

        employee_tasks = get_employee_tasks(self.employee.id, self.db)
        assert [task.id for task in employee_tasks] == [assigned_task.id]

    def test_task_assignment_and_schema_validation(self) -> None:
        with self.assertRaises(HTTPException) as error:
            create_task(self.task_data(project_id=uuid.uuid4()), self.db)
        assert error.exception.status_code == 404

        with self.assertRaises(HTTPException) as error:
            create_task(self.task_data(employee_id=uuid.uuid4()), self.db)
        assert error.exception.status_code == 404

        with self.assertRaises(HTTPException) as error:
            create_task(self.task_data(employee_id=self.unassigned_employee.id), self.db)
        assert error.exception.status_code == 400

        invalid_status_data = self.task_data().model_dump()
        invalid_status_data["status"] = "invalid"
        with self.assertRaises(ValidationError):
            TaskCreate(**invalid_status_data)

        invalid_priority_data = self.task_data().model_dump()
        invalid_priority_data["priority"] = "invalid"
        with self.assertRaises(ValidationError):
            TaskCreate(**invalid_priority_data)
