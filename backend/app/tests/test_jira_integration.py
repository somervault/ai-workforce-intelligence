import base64
import json
import unittest

import httpx

from app.integrations.jira_client import (
    ISSUE_FIELDS,
    JiraAuthenticationError,
    JiraClient,
    JiraHttpError,
    JiraMalformedResponseError,
    JiraTimeoutError,
)
from app.integrations.jira_service import JiraService


def jira_client(handler) -> JiraClient:
    return JiraClient(
        base_url="https://example.atlassian.net",
        email="integration@example.com",
        api_token="test-api-token",
        transport=httpx.MockTransport(handler),
    )


def issue_payload(issue_id: str = "10001", issue_key: str = "ENG-1") -> dict:
    return {
        "id": issue_id,
        "key": issue_key,
        "fields": {
            "project": {"id": "10000", "key": "ENG", "name": "Engineering"},
            "summary": "Build dashboard",
            "status": {"name": "In Progress"},
            "priority": {"name": "High"},
            "assignee": {"accountId": "account-1", "displayName": "Ada Lovelace"},
            "issuetype": {"name": "Task"},
            "created": "2026-08-10T10:00:00.000+0000",
            "updated": "2026-08-11T10:00:00.000+0000",
            "resolutiondate": None,
        },
    }


class TestJiraIntegration(unittest.TestCase):
    def test_authentication_header_and_project_retrieval(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            expected = base64.b64encode(
                b"integration@example.com:test-api-token"
            ).decode()
            assert request.headers["Authorization"] == f"Basic {expected}"
            assert request.url.path == "/rest/api/3/project/search"
            return httpx.Response(
                200,
                json={
                    "values": [
                        {
                            "id": "10000",
                            "key": "ENG",
                            "name": "Engineering",
                            "projectTypeKey": "software",
                        }
                    ],
                    "isLast": True,
                },
            )

        client = jira_client(handler)
        try:
            projects = JiraService(client).get_projects()
        finally:
            client.close()

        assert projects[0].key == "ENG"
        assert projects[0].project_type == "software"

    def test_project_pagination(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            start_at = request.url.params["startAt"]
            if start_at == "0":
                return httpx.Response(
                    200,
                    json={
                        "values": [{"id": "1", "key": "ONE", "name": "One"}],
                        "isLast": False,
                    },
                )
            return httpx.Response(
                200,
                json={
                    "values": [{"id": "2", "key": "TWO", "name": "Two"}],
                    "isLast": True,
                },
            )

        client = jira_client(handler)
        try:
            projects = JiraService(client).get_projects()
        finally:
            client.close()

        assert [project.key for project in projects] == ["ONE", "TWO"]

    def test_issue_search_uses_explicit_fields_and_pagination(self) -> None:
        requests: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            requests.append(body)
            if "nextPageToken" not in body:
                return httpx.Response(
                    200,
                    json={"issues": [issue_payload()], "nextPageToken": "next-page"},
                )
            return httpx.Response(
                200,
                json={"issues": [issue_payload("10002", "ENG-2")]},
            )

        client = jira_client(handler)
        try:
            issues = JiraService(client).search_issues("project = ENG")
        finally:
            client.close()

        assert [issue.key for issue in issues] == ["ENG-1", "ENG-2"]
        assert requests[0]["fields"] == ISSUE_FIELDS
        assert requests[1]["nextPageToken"] == "next-page"

    def test_issue_retrieval(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/rest/api/3/issue/ENG-1"
            assert set(request.url.params["fields"].split(",")) == set(ISSUE_FIELDS)
            return httpx.Response(200, json=issue_payload())

        client = jira_client(handler)
        try:
            issue = JiraService(client).get_issue("ENG-1")
        finally:
            client.close()

        assert issue.assignee_display_name == "Ada Lovelace"
        assert issue.priority == "High"

    def test_changelog_retrieval_and_pagination(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.params["startAt"] == "0":
                return httpx.Response(
                    200,
                    json={
                        "values": [
                            {
                                "id": "1",
                                "created": "2026-08-10T10:00:00.000+0000",
                                "author": {
                                    "accountId": "account-1",
                                    "displayName": "Ada Lovelace",
                                },
                                "items": [
                                    {
                                        "field": "status",
                                        "fromString": "To Do",
                                        "toString": "In Progress",
                                    }
                                ],
                            }
                        ],
                        "isLast": False,
                    },
                )
            return httpx.Response(
                200,
                json={
                    "values": [
                        {"id": "2", "author": None, "items": []}
                    ],
                    "isLast": True,
                },
            )

        client = jira_client(handler)
        try:
            activity = JiraService(client).get_issue_activity("ENG-1")
        finally:
            client.close()

        assert len(activity) == 2
        assert activity[0].items[0].to_value == "In Progress"

    def test_http_and_authentication_errors(self) -> None:
        authentication_client = jira_client(lambda request: httpx.Response(401))
        try:
            with self.assertRaises(JiraAuthenticationError):
                authentication_client.get_projects()
        finally:
            authentication_client.close()

        error_client = jira_client(lambda request: httpx.Response(500))
        try:
            with self.assertRaises(JiraHttpError) as error:
                error_client.get_projects()
        finally:
            error_client.close()
        assert error.exception.status_code == 500

    def test_timeout_and_malformed_response_errors(self) -> None:
        def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out", request=request)

        timeout_client = jira_client(timeout_handler)
        try:
            with self.assertRaises(JiraTimeoutError):
                timeout_client.get_projects()
        finally:
            timeout_client.close()

        malformed_client = jira_client(lambda request: httpx.Response(200, json={}))
        try:
            with self.assertRaises(JiraMalformedResponseError):
                malformed_client.get_projects()
        finally:
            malformed_client.close()
