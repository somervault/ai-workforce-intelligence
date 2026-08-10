from typing import Any

import httpx


class JiraIntegrationError(Exception):
    """Base error for Jira integration failures."""


class JiraConfigurationError(JiraIntegrationError):
    pass


class JiraAuthenticationError(JiraIntegrationError):
    pass


class JiraHttpError(JiraIntegrationError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"Jira returned HTTP {status_code}")


class JiraTimeoutError(JiraIntegrationError):
    pass


class JiraRequestError(JiraIntegrationError):
    pass


class JiraMalformedResponseError(JiraIntegrationError):
    pass


ISSUE_FIELDS = [
    "project",
    "summary",
    "status",
    "priority",
    "assignee",
    "issuetype",
    "created",
    "updated",
    "resolutiondate",
]


class JiraClient:
    """Read-only client for Jira Cloud REST API v3."""

    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ):
        if not base_url or not email or not api_token:
            raise JiraConfigurationError(
                "JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN must be configured"
            )
        if timeout_seconds <= 0:
            raise JiraConfigurationError("JIRA_REQUEST_TIMEOUT_SECONDS must be positive")

        self._client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/",
            auth=httpx.BasicAuth(email, api_token),
            headers={"Accept": "application/json"},
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def get_projects(self, page_size: int = 50) -> list[dict[str, Any]]:
        projects: list[dict[str, Any]] = []
        start_at = 0

        while True:
            response = self._request_json(
                "GET",
                "rest/api/3/project/search",
                params={"startAt": start_at, "maxResults": page_size},
            )
            values = self._list_value(response, "values")
            projects.extend(values)

            if response.get("isLast") is True:
                break
            total = response.get("total")
            next_start = start_at + len(values)
            if isinstance(total, int) and next_start >= total:
                break
            if not values:
                break
            start_at = next_start

        return projects

    def search_issues(
        self, jql: str, page_size: int = 50
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        next_page_token: str | None = None

        while True:
            payload: dict[str, Any] = {
                "jql": jql,
                "fields": ISSUE_FIELDS,
                "maxResults": page_size,
            }
            if next_page_token is not None:
                payload["nextPageToken"] = next_page_token

            response = self._request_json(
                "POST", "rest/api/3/search/jql", json=payload
            )
            issues.extend(self._list_value(response, "issues"))
            next_page_token = response.get("nextPageToken")
            if next_page_token is None:
                break
            if not isinstance(next_page_token, str):
                raise JiraMalformedResponseError("nextPageToken must be a string")

        return issues

    def get_issue(self, issue_id_or_key: str) -> dict[str, Any]:
        return self._request_json(
            "GET",
            f"rest/api/3/issue/{issue_id_or_key}",
            params={"fields": ",".join(ISSUE_FIELDS)},
        )

    def get_issue_changelog(
        self, issue_id_or_key: str, page_size: int = 50
    ) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        start_at = 0

        while True:
            response = self._request_json(
                "GET",
                f"rest/api/3/issue/{issue_id_or_key}/changelog",
                params={"startAt": start_at, "maxResults": page_size},
            )
            values = self._list_value(response, "values")
            changes.extend(values)

            if response.get("isLast") is True:
                break
            total = response.get("total")
            next_start = start_at + len(values)
            if isinstance(total, int) and next_start >= total:
                break
            if not values:
                break
            start_at = next_start

        return changes

    def _request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as error:
            raise JiraTimeoutError("Jira request timed out") from error
        except httpx.RequestError as error:
            raise JiraRequestError("Jira request failed") from error

        if response.status_code == 401:
            raise JiraAuthenticationError("Jira authentication failed")
        if response.is_error:
            raise JiraHttpError(response.status_code)

        try:
            payload = response.json()
        except ValueError as error:
            raise JiraMalformedResponseError("Jira returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise JiraMalformedResponseError("Jira response must be a JSON object")
        return payload

    @staticmethod
    def _list_value(payload: dict[str, Any], field_name: str) -> list[dict[str, Any]]:
        value = payload.get(field_name)
        if not isinstance(value, list) or not all(
            isinstance(item, dict) for item in value
        ):
            raise JiraMalformedResponseError(
                f"Jira response field '{field_name}' must be a list of objects"
            )
        return value
