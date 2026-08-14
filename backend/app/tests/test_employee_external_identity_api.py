import unittest
import uuid

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.workforce_activity_repository import WorkforceActivityRepository
from app.ai.workforce_activity_service import WorkforceActivityService
from app.database.base import Base
from app.integrations.github_schemas import GitHubCommitDTO, GitHubPullRequestDTO, GitHubRepositoryDTO, GitHubUserDTO
from app.integrations.jira_schemas import JiraAccountDTO, JiraIssueDTO
from app.models.department import Department
from app.models.employee import Employee
from app.models.employee_external_identity import EmployeeExternalIdentity
from app.schemas.employee_external_identity import EmployeeExternalIdentityCreate
from app.services.employee_external_identity_service import (
    EmployeeExternalIdentityConflictError,
    EmployeeExternalIdentityService,
    EmployeeExternalIdentityVerificationError,
)


test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


class FakeJiraService:
    def __init__(self, error: Exception | None = None): self.error = error
    def verify_account_id(self, account_id: str) -> JiraAccountDTO:
        if self.error: raise self.error
        return JiraAccountDTO(account_id=account_id, active=True)
    def search_issues(self, *args, **kwargs):
        return [JiraIssueDTO(id="1", key="A-1", project_id="1", project_key="A", project_name="A", summary="private", assignee_account_id="jira-1")]


class FakeGitHubService:
    def __init__(self, error: Exception | None = None): self.error = error
    def verify_user_id(self, user_id: str) -> GitHubUserDTO:
        if self.error: raise self.error
        return GitHubUserDTO(id=int(user_id), login="non-authoritative-login")
    def get_repositories(self, **kwargs):
        return [GitHubRepositoryDTO(id=1, owner_login="org", name="repo", full_name="org/repo", private=True, archived=False)]
    def get_commits(self, *args, **kwargs): return [GitHubCommitDTO(sha="a", author_id=42)]
    def get_pull_requests(self, *args, **kwargs): return [GitHubPullRequestDTO(number=1, title="private", state="open", draft=False, author_id=999)]
    def get_pull_request_reviews(self, *args, **kwargs): return []


class TestEmployeeExternalIdentityAPI(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.drop_all(bind=test_engine)
        Base.metadata.create_all(bind=test_engine)
        self.db: Session = TestSessionLocal()
        department = Department(name="Engineering")
        self.employee = Employee(employee_code="EMP-001", first_name="Ada", last_name="Lovelace", email="ada@example.com", designation="Engineer", department=department)
        self.other_employee = Employee(employee_code="EMP-002", first_name="Grace", last_name="Hopper", email="grace@example.com", designation="Engineer", department=department)
        self.db.add_all([self.employee, self.other_employee]); self.db.commit()

    def tearDown(self) -> None: self.db.close()

    def service(self, jira=None, github=None):
        return EmployeeExternalIdentityService(self.db, jira or FakeJiraService(), github or FakeGitHubService())

    def test_employee_and_provider_validation(self) -> None:
        with self.assertRaises(LookupError):
            self.service().create_mapping(uuid.uuid4(), EmployeeExternalIdentityCreate(provider="jira", external_id="jira-1"))
        with self.assertRaises(ValidationError):
            EmployeeExternalIdentityCreate(provider="invalid", external_id="x")

    def test_valid_jira_and_github_mappings_and_listing(self) -> None:
        service = self.service()
        jira = service.create_mapping(self.employee.id, EmployeeExternalIdentityCreate(provider="jira", external_id="jira-1"))
        github = service.create_mapping(self.other_employee.id, EmployeeExternalIdentityCreate(provider="github", external_id="42"))
        assert jira.external_login is None
        assert github.external_login == "non-authoritative-login"
        assert len(service.get_employee_mappings(self.employee.id)) == 1
        assert service.get_mapping(github.id).external_id == "42"

    def test_duplicate_active_identity_and_employee_provider_conflicts(self) -> None:
        service = self.service()
        service.create_mapping(self.employee.id, EmployeeExternalIdentityCreate(provider="jira", external_id="jira-1"))
        with self.assertRaises(EmployeeExternalIdentityConflictError):
            service.create_mapping(self.other_employee.id, EmployeeExternalIdentityCreate(provider="jira", external_id="jira-1"))
        with self.assertRaises(EmployeeExternalIdentityConflictError):
            service.create_mapping(self.employee.id, EmployeeExternalIdentityCreate(provider="jira", external_id="jira-2"))

    def test_historical_mapping_verification_and_soft_deactivation(self) -> None:
        service = self.service()
        mapping = service.create_mapping(self.employee.id, EmployeeExternalIdentityCreate(provider="jira", external_id="jira-1"))
        assert service.deactivate_mapping(mapping.id).status == "inactive"
        replacement = service.create_mapping(self.employee.id, EmployeeExternalIdentityCreate(provider="jira", external_id="jira-2"))
        assert replacement.status == "active"
        assert len(service.get_employee_mappings(self.employee.id)) == 2
        verified = service.verify_mapping(replacement.id)
        assert verified.verified_at is not None

    def test_verification_failure_does_not_create_or_change_mapping(self) -> None:
        with self.assertRaises(EmployeeExternalIdentityVerificationError):
            self.service(jira=FakeJiraService(RuntimeError("temporary"))).create_mapping(self.employee.id, EmployeeExternalIdentityCreate(provider="jira", external_id="jira-1"))
        assert self.service().get_employee_mappings(self.employee.id) == []
        mapping = self.service().create_mapping(self.employee.id, EmployeeExternalIdentityCreate(provider="jira", external_id="jira-1"))
        with self.assertRaises(EmployeeExternalIdentityVerificationError):
            self.service(jira=FakeJiraService(RuntimeError("temporary"))).verify_mapping(mapping.id)
        assert self.service().get_mapping(mapping.id).status == "active"

    def test_exact_id_attribution_and_unmapped_activity(self) -> None:
        service = self.service()
        service.create_mapping(self.employee.id, EmployeeExternalIdentityCreate(provider="jira", external_id="jira-1"))
        service.create_mapping(self.employee.id, EmployeeExternalIdentityCreate(provider="github", external_id="42"))
        result = WorkforceActivityService(WorkforceActivityRepository(self.db), FakeJiraService(), FakeGitHubService()).analyze()
        employee = next(item for item in result.employees if item.employee.id == self.employee.id)
        assert employee.raw_counts.jira_activity_events == 1
        assert employee.raw_counts.github_activity_events == 1
        assert result.unattributed_external_activity.github_pull_request_count == 1
        assert "ada@example.com" not in result.model_dump_json()

    def test_inactive_mappings_are_not_used_for_attribution(self) -> None:
        mapping = self.service().create_mapping(self.employee.id, EmployeeExternalIdentityCreate(provider="jira", external_id="jira-1"))
        self.service().deactivate_mapping(mapping.id)
        result = WorkforceActivityService(WorkforceActivityRepository(self.db), FakeJiraService(), FakeGitHubService()).analyze()
        employee = next(item for item in result.employees if item.employee.id == self.employee.id)
        assert employee.raw_counts.jira_activity_events == 0
        assert result.unattributed_external_activity.jira_issue_count == 1

    def test_deleted_mappings_are_not_used_for_attribution(self) -> None:
        mapping = self.service().create_mapping(self.employee.id, EmployeeExternalIdentityCreate(provider="jira", external_id="jira-1"))
        self.db.query(EmployeeExternalIdentity).filter_by(id=mapping.id).update({"status": "deleted"})
        self.db.commit()
        result = WorkforceActivityService(WorkforceActivityRepository(self.db), FakeJiraService(), FakeGitHubService()).analyze()
        employee = next(item for item in result.employees if item.employee.id == self.employee.id)
        assert employee.raw_counts.jira_activity_events == 0
        assert result.unattributed_external_activity.jira_issue_count == 1
