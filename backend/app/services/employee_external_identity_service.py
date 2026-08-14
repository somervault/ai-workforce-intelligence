import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.github_client import GitHubHttpError
from app.integrations.github_service import GitHubService
from app.integrations.jira_client import JiraHttpError
from app.integrations.jira_service import JiraService
from app.models.employee import Employee
from app.models.employee_external_identity import EmployeeExternalIdentity
from app.repositories.employee_external_identity_repository import EmployeeExternalIdentityRepository
from app.schemas.employee_external_identity import EmployeeExternalIdentityCreate


class EmployeeExternalIdentityConflictError(Exception):
    pass


class EmployeeExternalIdentityVerificationError(Exception):
    pass


class EmployeeExternalIdentityService:
    def __init__(self, db: Session, jira_service: JiraService | None = None, github_service: GitHubService | None = None):
        self.db = db
        self.repository = EmployeeExternalIdentityRepository(db)
        self.jira_service = jira_service
        self.github_service = github_service

    def create_mapping(self, employee_id: uuid.UUID, data: EmployeeExternalIdentityCreate) -> EmployeeExternalIdentity:
        self._ensure_employee_exists(employee_id)
        if self.repository.get_active_by_external_id(data.provider, data.external_id):
            raise EmployeeExternalIdentityConflictError("External identity is already mapped to an employee")
        if self.repository.get_active_by_employee_provider(employee_id, data.provider):
            raise EmployeeExternalIdentityConflictError("Employee already has an active identity for this provider")
        try:
            external_login, status = self._verify_external_identity(data.provider, data.external_id)
        except Exception as error:
            raise EmployeeExternalIdentityVerificationError("External identity verification failed") from error
        identity = EmployeeExternalIdentity(
            employee_id=employee_id, provider=data.provider, external_id=data.external_id,
            external_login=external_login, status=status, verified_at=datetime.now(UTC),
        )
        try:
            return self.repository.create(identity)
        except IntegrityError as error:
            self.db.rollback()
            raise EmployeeExternalIdentityConflictError("Active external identity mapping conflicts with an existing mapping") from error

    def get_mapping(self, mapping_id: uuid.UUID) -> EmployeeExternalIdentity | None:
        return self.repository.get_by_id(mapping_id)

    def get_employee_mappings(self, employee_id: uuid.UUID) -> list[EmployeeExternalIdentity]:
        self._ensure_employee_exists(employee_id)
        return self.repository.get_by_employee_id(employee_id)

    def verify_mapping(self, mapping_id: uuid.UUID) -> EmployeeExternalIdentity | None:
        identity = self.repository.get_by_id(mapping_id)
        if identity is None:
            return None
        try:
            external_login, status = self._verify_external_identity(identity.provider, identity.external_id)
        except (JiraHttpError, GitHubHttpError) as error:
            if error.status_code == 404:
                return self.repository.update(identity, status="deleted")
            raise EmployeeExternalIdentityVerificationError("External identity verification failed") from error
        return self.repository.update(
            identity, external_login=external_login, status=status, verified_at=datetime.now(UTC)
        )

    def deactivate_mapping(self, mapping_id: uuid.UUID) -> EmployeeExternalIdentity | None:
        identity = self.repository.get_by_id(mapping_id)
        if identity is None:
            return None
        return self.repository.update(identity, status="inactive")

    def _verify_external_identity(self, provider: str, external_id: str) -> tuple[str | None, str]:
        try:
            if provider == "jira":
                if self.jira_service is None:
                    self.jira_service = JiraService()
                account = self.jira_service.verify_account_id(external_id)
                return None, "active" if account.active else "inactive"
            if provider == "github":
                if self.github_service is None:
                    self.github_service = GitHubService()
                user = self.github_service.verify_user_id(external_id)
                return user.login, "active"
        except (JiraHttpError, GitHubHttpError):
            raise
        except Exception as error:
            raise EmployeeExternalIdentityVerificationError("External identity verification failed") from error
        raise EmployeeExternalIdentityVerificationError("Unsupported external identity provider")

    def _ensure_employee_exists(self, employee_id: uuid.UUID) -> None:
        if self.db.get(Employee, employee_id) is None:
            raise LookupError("Employee not found")
