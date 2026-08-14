from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_external_identity import EmployeeExternalIdentity
from app.models.employee_project import EmployeeProject
from app.models.project import Project
from app.models.task import Task


@dataclass
class EmployeeWorkloadInput:
    employee: Employee
    tasks: list[Task]
    active_project_assignments: int
    jira_account_ids: set[str]
    github_user_ids: set[str]


class WorkforceActivityRepository:
    """Read-only data access for workforce analysis."""

    def __init__(self, db: Session):
        self.db = db

    def get_employee_workload_inputs(self) -> list[EmployeeWorkloadInput]:
        employees = list(self.db.scalars(select(Employee).order_by(Employee.employee_code)))
        tasks_by_employee: dict[uuid.UUID, list[Task]] = defaultdict(list)
        assigned_tasks: Iterable[Task] = self.db.scalars(
            select(Task).where(Task.assigned_employee_id.is_not(None))
        )
        for task in assigned_tasks:
            if task.assigned_employee_id is not None:
                tasks_by_employee[task.assigned_employee_id].append(task)

        active_assignments: dict[uuid.UUID, int] = defaultdict(int)
        assignments = self.db.execute(
            select(EmployeeProject.employee_id)
            .join(Project, EmployeeProject.project_id == Project.id)
            .where(Project.status == "active")
        )
        for (employee_id,) in assignments:
            active_assignments[employee_id] += 1

        jira_ids: dict[uuid.UUID, set[str]] = defaultdict(set)
        github_ids: dict[uuid.UUID, set[str]] = defaultdict(set)
        identities = self.db.scalars(select(EmployeeExternalIdentity).where(EmployeeExternalIdentity.status == "active"))
        for identity in identities:
            if identity.provider == "jira":
                jira_ids[identity.employee_id].add(identity.external_id)
            elif identity.provider == "github":
                github_ids[identity.employee_id].add(identity.external_id)

        return [
            EmployeeWorkloadInput(
                employee=employee,
                tasks=tasks_by_employee[employee.id],
                active_project_assignments=active_assignments[employee.id],
                jira_account_ids=jira_ids[employee.id],
                github_user_ids=github_ids[employee.id],
            )
            for employee in employees
        ]
