import unittest
import uuid
from datetime import UTC, date, datetime, timedelta

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.workforce_activity_repository import WorkforceActivityRepository
from app.ai.workforce_activity_scoring import classify_workload
from app.ai.workforce_activity_schemas import WorkforceAnalysisConfiguration
from app.ai.workforce_activity_service import WorkforceActivityService
from app.database.base import Base
from app.integrations.github_schemas import (
    GitHubCommitDTO,
    GitHubPullRequestDTO,
    GitHubPullRequestReviewDTO,
    GitHubRepositoryDTO,
)
from app.integrations.jira_schemas import JiraIssueDTO
from app.models.department import Department
from app.models.employee import Employee
from app.models.employee_project import EmployeeProject
from app.models.project import Project
from app.models.task import Task


test_engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
NOW = datetime(2026, 8, 12, 12, tzinfo=UTC)


class FakeJiraService:
    def __init__(self, issues: list[object] | None = None):
        self.issues = issues or []
        self.calls: list[dict] = []

    def search_issues(self, jql: str, **kwargs: int) -> list[object]:
        self.calls.append({"jql": jql, **kwargs})
        return self.issues


class FakeGitHubService:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.repository = GitHubRepositoryDTO(
            id=1, owner_login="org", name="repo", full_name="org/repo",
            private=True, archived=False,
        )

    def get_repositories(self, **kwargs: int):
        self.calls.append(("repositories", kwargs))
        return [self.repository]

    def get_commits(self, *args: object, **kwargs: object):
        self.calls.append(("commits", kwargs))
        return [GitHubCommitDTO(sha="a"), GitHubCommitDTO(sha="b")]

    def get_pull_requests(self, *args: object, **kwargs: int):
        self.calls.append(("pull_requests", kwargs))
        return [GitHubPullRequestDTO(number=1, title="PR", state="open", draft=False)]

    def get_pull_request_reviews(self, *args: object, **kwargs: int):
        self.calls.append(("reviews", kwargs))
        return [GitHubPullRequestReviewDTO(id=1, state="APPROVED")]


class TestWorkforceActivityService(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.drop_all(bind=test_engine)
        Base.metadata.create_all(bind=test_engine)
        self.db: Session = TestSessionLocal()
        self.department = Department(name="Engineering")
        self.employee = Employee(
            employee_code="EMP-001", first_name="Ada", last_name="Lovelace",
            email="ada@example.com", designation="Engineer", department=self.department,
        )
        self.empty_employee = Employee(
            employee_code="EMP-002", first_name="Grace", last_name="Hopper",
            email="grace@example.com", designation="Engineer", department=self.department,
        )
        self.active_project = Project(name="Active", status="active")
        self.db.add_all([self.employee, self.empty_employee, self.active_project])
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()

    def add_task(
        self, status: str, priority: str, due_date: date | None = None,
        created_at: datetime | None = None, updated_at: datetime | None = None,
    ) -> None:
        self.db.add(Task(
            project_id=self.active_project.id, title=str(uuid.uuid4()), status=status,
            priority=priority, assigned_employee_id=self.employee.id, due_date=due_date,
            created_at=created_at or NOW, updated_at=updated_at or NOW,
        ))
        self.db.commit()

    def analyze(self, jira=None, github=None):
        return WorkforceActivityService(
            WorkforceActivityRepository(self.db), jira_service=jira, github_service=github
        ).analyze(NOW)

    def test_empty_workload_and_explainability(self) -> None:
        result = self.analyze()
        empty = next(item for item in result.employees if item.employee.id == self.empty_employee.id)
        assert empty.workload_score == 0
        assert empty.activity_score == 0
        assert empty.classification == "underloaded"
        assert empty.raw_counts.assigned_open_tasks == 0
        assert empty.factors
        assert result.scoring_version == "workforce-v1"

    def test_priority_overdue_due_soon_project_load_and_completion_relief(self) -> None:
        self.db.add(EmployeeProject(employee_id=self.employee.id, project_id=self.active_project.id, role="Developer"))
        self.db.commit()
        self.add_task("todo", "critical", NOW.date() - timedelta(days=1))
        self.add_task("in_progress", "high", NOW.date() + timedelta(days=2))
        self.add_task("completed", "medium", updated_at=NOW - timedelta(days=1))
        analysis = next(item for item in self.analyze().employees if item.employee.id == self.employee.id)
        assert analysis.raw_counts.priority_weight_total == 7
        assert analysis.raw_counts.overdue_tasks == 1
        assert analysis.raw_counts.due_soon_tasks == 1
        assert analysis.raw_counts.active_project_assignments == 1
        assert analysis.raw_counts.completed_tasks_in_window == 1
        assert analysis.component_scores.open_task_score == 26.25
        assert analysis.component_scores.due_date_pressure_score == 12.5
        assert analysis.component_scores.active_project_load_score == round(20 / 3, 2)
        assert analysis.component_scores.completion_relief_score == round(10 / 3, 2)
        assert any("overdue" in factor for factor in analysis.factors)
        assert any("due soon" in factor for factor in analysis.factors)
        assert any("completed" in factor for factor in analysis.factors)

    def test_classification_boundaries(self) -> None:
        configuration = WorkforceAnalysisConfiguration()
        assert classify_workload(34.99, configuration) == "underloaded"
        assert classify_workload(35, configuration) == "balanced"
        assert classify_workload(69.99, configuration) == "balanced"
        assert classify_workload(70, configuration) == "overloaded"

    def test_unattributed_external_activity_and_bounded_queries(self) -> None:
        jira = FakeJiraService([
            JiraIssueDTO(id="1", key="A-1", project_id="1", project_key="A", project_name="A", summary="x"),
            JiraIssueDTO(id="2", key="A-2", project_id="1", project_key="A", project_name="A", summary="x"),
        ])
        github = FakeGitHubService()
        result = self.analyze(jira, github)
        external = result.unattributed_external_activity
        assert external.jira_issue_count == 2
        assert external.github_commit_count == 2
        assert external.github_pull_request_count == 1
        assert external.github_review_count == 1
        assert jira.calls[0]["max_pages"] == 1
        assert jira.calls[0]["max_results"] == 25
        assert all(call[1]["max_pages"] == 1 for call in github.calls)
        employee = next(item for item in result.employees if item.employee.id == self.employee.id)
        assert employee.activity_score == employee.component_scores.internal_task_activity_score
        assert "not attributed" in external.factors[0]

    def test_privacy_data_minimization(self) -> None:
        self.add_task("todo", "high")
        result = self.analyze(FakeJiraService([JiraIssueDTO(
            id="1", key="ENG-1", project_id="1", project_key="ENG",
            project_name="Engineering", summary="Excluded from analysis output"
        )]), FakeGitHubService())
        payload = result.model_dump_json()
        assert "ada@example.com" not in payload
        assert "Excluded from analysis output" not in payload
        assert "message" not in payload
        assert "body" not in payload

    def test_invalid_configuration(self) -> None:
        with self.assertRaises(ValidationError):
            WorkforceAnalysisConfiguration(underloaded_threshold=70, overloaded_threshold=70)
        with self.assertRaises(ValidationError):
            WorkforceAnalysisConfiguration(open_task_weight=44)
