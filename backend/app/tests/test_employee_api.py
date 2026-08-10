import unittest
import uuid

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.employee import (
    create_employee,
    delete_employee,
    get_employee,
    get_employees,
    update_employee,
)
from app.database.base import Base
from app.models.department import Department
from app.models.employee import Employee  # Register Employee with Base metadata.
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


class TestEmployeeAPI(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.drop_all(bind=test_engine)
        Base.metadata.create_all(bind=test_engine)
        self.db: Session = TestSessionLocal()
        department = Department(name="Engineering", description="Product engineering")
        self.db.add(department)
        self.db.commit()
        self.db.refresh(department)
        self.department_id = department.id

    def tearDown(self) -> None:
        self.db.close()

    def employee_data(self, department_id: uuid.UUID | None = None) -> EmployeeCreate:
        return EmployeeCreate(
            employee_code="EMP-001",
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            designation="Engineer",
            department_id=department_id or self.department_id,
        )

    def test_employee_crud(self) -> None:
        created = create_employee(self.employee_data(), self.db)
        assert created.employee_code == "EMP-001"

        listed = get_employees(self.db)
        assert len(listed) == 1

        fetched = get_employee(created.id, self.db)
        assert fetched.email == "ada@example.com"

        updated = update_employee(
            created.id, EmployeeUpdate(designation="Senior Engineer"), self.db
        )
        assert updated.designation == "Senior Engineer"

        assert delete_employee(created.id, self.db) is None
        with self.assertRaises(HTTPException) as error:
            get_employee(created.id, self.db)
        assert error.exception.status_code == 404

    def test_employee_validation_and_conflicts(self) -> None:
        create_employee(self.employee_data(), self.db)

        with self.assertRaises(HTTPException) as error:
            create_employee(self.employee_data(), self.db)
        assert error.exception.status_code == 409

        with self.assertRaises(HTTPException) as error:
            create_employee(self.employee_data(uuid.uuid4()), self.db)
        assert error.exception.status_code == 400

        with self.assertRaises(HTTPException) as error:
            get_employee(uuid.uuid4(), self.db)
        assert error.exception.status_code == 404

        invalid_email_data = self.employee_data().model_dump()
        invalid_email_data["email"] = "not-an-email"
        with self.assertRaises(ValidationError):
            EmployeeCreate(**invalid_email_data)
