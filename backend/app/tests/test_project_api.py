import unittest
import uuid
from datetime import date

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.project import (
    create_project,
    delete_project,
    get_project,
    get_projects,
    update_project,
)
from app.database.base import Base
from app.models.project import Project  # Register Project with Base metadata.
from app.schemas.project import ProjectCreate, ProjectUpdate


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


class TestProjectAPI(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.drop_all(bind=test_engine)
        Base.metadata.create_all(bind=test_engine)
        self.db: Session = TestSessionLocal()

    def tearDown(self) -> None:
        self.db.close()

    @staticmethod
    def project_data() -> ProjectCreate:
        return ProjectCreate(
            name="Platform upgrade",
            description="Upgrade the workforce platform.",
            status="planned",
            start_date=date(2026, 8, 10),
            end_date=date(2026, 9, 10),
        )

    def test_project_crud(self) -> None:
        created = create_project(self.project_data(), self.db)
        assert created.name == "Platform upgrade"
        assert created.status == "planned"

        listed = get_projects(self.db)
        assert len(listed) == 1

        fetched = get_project(created.id, self.db)
        assert fetched.id == created.id

        updated = update_project(
            created.id,
            ProjectUpdate(status="active", end_date=date(2026, 10, 1)),
            self.db,
        )
        assert updated.status == "active"
        assert updated.end_date == date(2026, 10, 1)

        assert delete_project(created.id, self.db) is None
        with self.assertRaises(HTTPException) as error:
            get_project(created.id, self.db)
        assert error.exception.status_code == 404

    def test_project_validation_and_not_found(self) -> None:
        with self.assertRaises(ValidationError):
            ProjectCreate(name="Invalid", status="unknown")

        with self.assertRaises(ValidationError):
            ProjectCreate(
                name="Invalid dates",
                status="planned",
                start_date=date(2026, 9, 1),
                end_date=date(2026, 8, 1),
            )

        project = create_project(self.project_data(), self.db)
        with self.assertRaises(HTTPException) as error:
            update_project(
                project.id,
                ProjectUpdate(end_date=date(2026, 8, 1)),
                self.db,
            )
        assert error.exception.status_code == 400

        with self.assertRaises(HTTPException) as error:
            get_project(uuid.uuid4(), self.db)
        assert error.exception.status_code == 404
