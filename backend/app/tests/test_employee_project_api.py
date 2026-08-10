import unittest
import uuid

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.employee_project import (
    assign_employee_to_project,
    get_employee_projects,
    get_project_employees,
    remove_employee_from_project,
)
from app.database.base import Base
from app.models.department import Department
from app.models.employee import Employee
from app.models.employee_project import EmployeeProject
from app.models.project import Project
from app.schemas.employee_project import EmployeeProjectCreate


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


class TestEmployeeProjectAPI(unittest.TestCase):
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
        self.project = Project(name="Platform upgrade", status="planned")
        self.db.add_all([self.employee, self.project])
        self.db.commit()
        self.db.refresh(self.employee)
        self.db.refresh(self.project)

    def tearDown(self) -> None:
        self.db.close()

    @staticmethod
    def assignment_data(role: str = "Developer") -> EmployeeProjectCreate:
        return EmployeeProjectCreate(role=role)

    def test_assign_and_list_assignments(self) -> None:
        assignment = assign_employee_to_project(
            self.project.id, self.employee.id, self.assignment_data(), self.db
        )
        assert assignment.role == "Developer"

        project_assignments = get_project_employees(self.project.id, self.db)
        assert len(project_assignments) == 1
        assert project_assignments[0].employee_id == self.employee.id

        employee_assignments = get_employee_projects(self.employee.id, self.db)
        assert len(employee_assignments) == 1
        assert employee_assignments[0].project_id == self.project.id

    def test_duplicate_and_missing_assignments(self) -> None:
        assign_employee_to_project(
            self.project.id, self.employee.id, self.assignment_data(), self.db
        )
        with self.assertRaises(HTTPException) as error:
            assign_employee_to_project(
                self.project.id, self.employee.id, self.assignment_data(), self.db
            )
        assert error.exception.status_code == 409

        with self.assertRaises(HTTPException) as error:
            assign_employee_to_project(
                self.project.id, uuid.uuid4(), self.assignment_data(), self.db
            )
        assert error.exception.status_code == 404

        with self.assertRaises(HTTPException) as error:
            assign_employee_to_project(
                uuid.uuid4(), self.employee.id, self.assignment_data(), self.db
            )
        assert error.exception.status_code == 404

    def test_remove_assignment(self) -> None:
        assign_employee_to_project(
            self.project.id, self.employee.id, self.assignment_data(), self.db
        )
        assert remove_employee_from_project(self.project.id, self.employee.id, self.db) is None
        assert get_project_employees(self.project.id, self.db) == []

        with self.assertRaises(HTTPException) as error:
            remove_employee_from_project(self.project.id, self.employee.id, self.db)
        assert error.exception.status_code == 404
