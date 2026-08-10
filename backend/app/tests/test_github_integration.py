import unittest
from datetime import UTC, datetime

import httpx

from app.integrations.github_client import (
    GITHUB_API_VERSION,
    GitHubAuthenticationError,
    GitHubClient,
    GitHubHttpError,
    GitHubMalformedResponseError,
    GitHubPaginationError,
    GitHubRateLimitError,
    GitHubTimeoutError,
)
from app.integrations.github_service import GitHubService


def github_client(handler) -> GitHubClient:
    return GitHubClient(
        api_base_url="https://api.github.com",
        token="test-github-token",
        org="example-org",
        transport=httpx.MockTransport(handler),
    )


def repository_payload(repository_id: int = 1, name: str = "platform") -> dict:
    return {
        "id": repository_id,
        "owner": {"login": "example-org"},
        "name": name,
        "full_name": f"example-org/{name}",
        "private": True,
        "archived": False,
        "default_branch": "main",
        "pushed_at": "2026-08-10T10:00:00Z",
        "updated_at": "2026-08-11T10:00:00Z",
    }


def commit_payload() -> dict:
    return {
        "sha": "abc123",
        "author": {"login": "ada"},
        "committer": {"login": "ada"},
        "commit": {
            "author": {"date": "2026-08-10T10:00:00Z"},
            "committer": {"date": "2026-08-10T10:30:00Z"},
            "message": "This must not be included in the DTO",
        },
    }


class TestGitHubIntegration(unittest.TestCase):
    def test_authentication_headers_and_authenticated_user(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["Authorization"] == "Bearer test-github-token"
            assert request.headers["Accept"] == "application/vnd.github+json"
            assert request.headers["X-GitHub-Api-Version"] == GITHUB_API_VERSION
            assert request.url.path == "/user"
            return httpx.Response(200, json={"id": 1, "login": "ada"})

        client = github_client(handler)
        try:
            user = GitHubService(client).get_authenticated_user()
        finally:
            client.close()
        assert user.login == "ada"

    def test_repository_retrieval_and_link_pagination(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.params["page"] == "1":
                return httpx.Response(
                    200,
                    headers={
                        "Link": '<https://api.github.com/orgs/example-org/repos?page=2&per_page=50>; rel="next"'
                    },
                    json=[repository_payload()],
                )
            return httpx.Response(200, json=[repository_payload(2, "api")])

        client = github_client(handler)
        try:
            repositories = GitHubService(client).get_repositories()
        finally:
            client.close()
        assert [repository.name for repository in repositories] == ["platform", "api"]

    def test_commit_retrieval_and_since_until_parameters(self) -> None:
        since = datetime(2026, 8, 1, tzinfo=UTC)
        until = datetime(2026, 8, 2, tzinfo=UTC)

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/repos/example-org/platform/commits"
            assert request.url.params["since"] == "2026-08-01T00:00:00Z"
            assert request.url.params["until"] == "2026-08-02T00:00:00Z"
            return httpx.Response(200, json=[commit_payload()])

        client = github_client(handler)
        try:
            commits = GitHubService(client).get_commits(
                "example-org", "platform", since, until
            )
        finally:
            client.close()
        assert commits[0].sha == "abc123"
        assert not hasattr(commits[0], "message")

    def test_pull_request_retrieval(self) -> None:
        payload = {
            "number": 12,
            "title": "Improve dashboard",
            "state": "open",
            "draft": False,
            "user": {"login": "ada"},
            "created_at": "2026-08-10T10:00:00Z",
            "updated_at": "2026-08-11T10:00:00Z",
            "merged_at": None,
        }
        client = github_client(lambda request: httpx.Response(200, json=[payload]))
        try:
            pull_requests = GitHubService(client).get_pull_requests(
                "example-org", "platform"
            )
        finally:
            client.close()
        assert pull_requests[0].number == 12
        assert pull_requests[0].author_login == "ada"

    def test_review_and_contributor_retrieval(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/reviews"):
                return httpx.Response(
                    200,
                    json=[
                        {
                            "id": 20,
                            "state": "APPROVED",
                            "user": {"login": "grace"},
                            "submitted_at": "2026-08-11T10:00:00Z",
                            "body": "This must not be included in the DTO",
                        }
                    ],
                )
            return httpx.Response(
                200, json=[{"id": 3, "login": "ada", "contributions": 42}]
            )

        client = github_client(handler)
        try:
            service = GitHubService(client)
            reviews = service.get_pull_request_reviews("example-org", "platform", 12)
            contributors = service.get_contributors("example-org", "platform")
        finally:
            client.close()
        assert reviews[0].state == "APPROVED"
        assert not hasattr(reviews[0], "body")
        assert contributors[0].contributions == 42

    def test_bounded_page_and_result_limits(self) -> None:
        request_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
            return httpx.Response(
                200,
                headers={
                    "Link": '<https://api.github.com/orgs/example-org/repos?page=2>; rel="next"'
                },
                json=[repository_payload(1), repository_payload(2, "api")],
            )

        client = github_client(handler)
        try:
            repositories = client.get_repositories(max_pages=1, max_results=1)
        finally:
            client.close()
        assert len(repositories) == 1
        assert request_count == 1

    def test_http_authentication_and_rate_limit_errors(self) -> None:
        authentication_client = github_client(lambda request: httpx.Response(401))
        try:
            with self.assertRaises(GitHubAuthenticationError):
                authentication_client.get_repositories()
        finally:
            authentication_client.close()

        error_client = github_client(lambda request: httpx.Response(500))
        try:
            with self.assertRaises(GitHubHttpError) as error:
                error_client.get_repositories()
        finally:
            error_client.close()
        assert error.exception.status_code == 500

        rate_limit_client = github_client(
            lambda request: httpx.Response(403, headers={"X-RateLimit-Remaining": "0"})
        )
        try:
            with self.assertRaises(GitHubRateLimitError):
                rate_limit_client.get_repositories()
        finally:
            rate_limit_client.close()

    def test_timeout_and_pagination_errors(self) -> None:
        def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out", request=request)

        timeout_client = github_client(timeout_handler)
        try:
            with self.assertRaises(GitHubTimeoutError):
                timeout_client.get_repositories()
        finally:
            timeout_client.close()

        malformed_client = github_client(lambda request: httpx.Response(200, json={}))
        try:
            with self.assertRaises(GitHubMalformedResponseError):
                malformed_client.get_repositories()
        finally:
            malformed_client.close()

        pagination_client = github_client(
            lambda request: httpx.Response(200, headers={"Link": 'rel="next"'}, json=[])
        )
        try:
            with self.assertRaises(GitHubPaginationError):
                pagination_client.get_repositories()
        finally:
            pagination_client.close()
