from typing import Any

from app.config.settings import settings
from app.integrations.jira_client import JiraClient, JiraMalformedResponseError
from app.integrations.jira_schemas import (
    JiraAccountDTO,
    JiraChangelogItemDTO,
    JiraIssueActivityDTO,
    JiraIssueDTO,
    JiraProjectDTO,
)


class JiraService:
    """Application-facing, read-only Jira integration service."""

    def __init__(self, client: JiraClient | None = None):
        self.client = client or JiraClient(
            base_url=settings.jira_base_url,
            email=settings.jira_email,
            api_token=settings.jira_api_token,
            timeout_seconds=settings.jira_request_timeout_seconds,
        )

    def get_projects(self) -> list[JiraProjectDTO]:
        return [self._project_from_raw(project) for project in self.client.get_projects()]

    def verify_account_id(self, account_id: str) -> JiraAccountDTO:
        account = self.client.get_user(account_id)
        returned_id = self._required_string(account, "accountId")
        if returned_id != account_id:
            raise JiraMalformedResponseError("Jira returned a different account ID")
        active = account.get("active", True)
        if not isinstance(active, bool):
            raise JiraMalformedResponseError("Jira account active flag must be boolean")
        return JiraAccountDTO(account_id=returned_id, active=active)

    def search_issues(
        self, jql: str = "order by updated DESC", page_size: int = 50,
        max_pages: int = 10, max_results: int = 500,
    ) -> list[JiraIssueDTO]:
        return [
            self._issue_from_raw(issue)
            for issue in self.client.search_issues(jql, page_size, max_pages, max_results)
        ]

    def get_issue(self, issue_id_or_key: str) -> JiraIssueDTO:
        return self._issue_from_raw(self.client.get_issue(issue_id_or_key))

    def get_issue_activity(
        self, issue_id_or_key: str, page_size: int = 50,
        max_pages: int = 10, max_results: int = 500,
    ) -> list[JiraIssueActivityDTO]:
        return [
            self._activity_from_raw(activity)
            for activity in self.client.get_issue_changelog(
                issue_id_or_key, page_size, max_pages, max_results
            )
        ]

    @staticmethod
    def _project_from_raw(project: dict[str, Any]) -> JiraProjectDTO:
        return JiraProjectDTO(
            id=JiraService._required_string(project, "id"),
            key=JiraService._required_string(project, "key"),
            name=JiraService._required_string(project, "name"),
            project_type=JiraService._optional_string(project, "projectTypeKey"),
        )

    @staticmethod
    def _issue_from_raw(issue: dict[str, Any]) -> JiraIssueDTO:
        fields = issue.get("fields")
        if not isinstance(fields, dict):
            raise JiraMalformedResponseError("Issue response is missing fields")
        project = fields.get("project")
        if not isinstance(project, dict):
            raise JiraMalformedResponseError("Issue response is missing project")

        status = JiraService._named_value(fields, "status")
        priority = JiraService._named_value(fields, "priority")
        issue_type = JiraService._named_value(fields, "issuetype")
        assignee = fields.get("assignee")
        if assignee is not None and not isinstance(assignee, dict):
            raise JiraMalformedResponseError("Issue assignee must be an object or null")

        return JiraIssueDTO(
            id=JiraService._required_string(issue, "id"),
            key=JiraService._required_string(issue, "key"),
            project_id=JiraService._required_string(project, "id"),
            project_key=JiraService._required_string(project, "key"),
            project_name=JiraService._required_string(project, "name"),
            summary=JiraService._required_string(fields, "summary"),
            status=status,
            priority=priority,
            assignee_account_id=(
                JiraService._optional_string(assignee, "accountId") if assignee else None
            ),
            assignee_display_name=(
                JiraService._optional_string(assignee, "displayName") if assignee else None
            ),
            issue_type=issue_type,
            created=JiraService._optional_string(fields, "created"),
            updated=JiraService._optional_string(fields, "updated"),
            resolution_date=JiraService._optional_string(fields, "resolutiondate"),
        )

    @staticmethod
    def _activity_from_raw(activity: dict[str, Any]) -> JiraIssueActivityDTO:
        author = activity.get("author")
        if author is not None and not isinstance(author, dict):
            raise JiraMalformedResponseError("Changelog author must be an object or null")
        items = activity.get("items")
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise JiraMalformedResponseError("Changelog items must be a list of objects")

        return JiraIssueActivityDTO(
            id=JiraService._required_string(activity, "id"),
            created=JiraService._optional_string(activity, "created"),
            author_account_id=(
                JiraService._optional_string(author, "accountId") if author else None
            ),
            author_display_name=(
                JiraService._optional_string(author, "displayName") if author else None
            ),
            items=[
                JiraChangelogItemDTO(
                    field=JiraService._required_string(item, "field"),
                    from_value=JiraService._optional_string(item, "fromString"),
                    to_value=JiraService._optional_string(item, "toString"),
                )
                for item in items
            ],
        )

    @staticmethod
    def _required_string(value: dict[str, Any], field_name: str) -> str:
        result = value.get(field_name)
        if not isinstance(result, str) or not result:
            raise JiraMalformedResponseError(
                f"Jira response field '{field_name}' must be a non-empty string"
            )
        return result

    @staticmethod
    def _optional_string(value: dict[str, Any], field_name: str) -> str | None:
        result = value.get(field_name)
        if result is None:
            return None
        if not isinstance(result, str):
            raise JiraMalformedResponseError(
                f"Jira response field '{field_name}' must be a string or null"
            )
        return result

    @staticmethod
    def _named_value(value: dict[str, Any], field_name: str) -> str | None:
        nested_value = value.get(field_name)
        if nested_value is None:
            return None
        if not isinstance(nested_value, dict):
            raise JiraMalformedResponseError(
                f"Jira response field '{field_name}' must be an object or null"
            )
        return JiraService._optional_string(nested_value, "name")
