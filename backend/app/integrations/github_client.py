import re
from datetime import datetime
from typing import Any

import httpx

GITHUB_API_VERSION = "2022-11-28"
DEFAULT_PAGE_SIZE = 50
DEFAULT_MAX_PAGES = 10
DEFAULT_MAX_RESULTS = 500


class GitHubIntegrationError(Exception):
    """Base error for GitHub integration failures."""


class GitHubConfigurationError(GitHubIntegrationError):
    pass


class GitHubAuthenticationError(GitHubIntegrationError):
    pass


class GitHubHttpError(GitHubIntegrationError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"GitHub returned HTTP {status_code}")


class GitHubRateLimitError(GitHubIntegrationError):
    pass


class GitHubTimeoutError(GitHubIntegrationError):
    pass


class GitHubRequestError(GitHubIntegrationError):
    pass


class GitHubMalformedResponseError(GitHubIntegrationError):
    pass


class GitHubPaginationError(GitHubIntegrationError):
    pass


class GitHubClient:
    """Read-only client for selected GitHub REST API endpoints."""

    def __init__(
        self,
        api_base_url: str,
        token: str,
        org: str,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ):
        if not api_base_url or not token or not org:
            raise GitHubConfigurationError(
                "GITHUB_API_BASE_URL, GITHUB_TOKEN, and GITHUB_ORG must be configured"
            )
        if timeout_seconds <= 0:
            raise GitHubConfigurationError(
                "GITHUB_REQUEST_TIMEOUT_SECONDS must be positive"
            )

        self.org = org
        self._client = httpx.Client(
            base_url=f"{api_base_url.rstrip('/')}/",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": GITHUB_API_VERSION,
            },
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def get_authenticated_user(self) -> dict[str, Any]:
        return self._json_object(self._request("GET", "user"))

    def get_repositories(
        self,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> list[dict[str, Any]]:
        return self._get_paginated(
            f"orgs/{self.org}/repos",
            params={"type": "all", "sort": "updated", "direction": "desc"},
            page_size=page_size,
            max_pages=max_pages,
            max_results=max_results,
        )

    def get_commits(
        self,
        owner: str,
        repo: str,
        since: datetime | None = None,
        until: datetime | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {}
        if since is not None:
            params["since"] = self._iso_timestamp(since)
        if until is not None:
            params["until"] = self._iso_timestamp(until)
        return self._get_paginated(
            f"repos/{owner}/{repo}/commits",
            params=params,
            page_size=page_size,
            max_pages=max_pages,
            max_results=max_results,
        )

    def get_pull_requests(
        self,
        owner: str,
        repo: str,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> list[dict[str, Any]]:
        return self._get_paginated(
            f"repos/{owner}/{repo}/pulls",
            params={"state": "all", "sort": "updated", "direction": "desc"},
            page_size=page_size,
            max_pages=max_pages,
            max_results=max_results,
        )

    def get_pull_request_reviews(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> list[dict[str, Any]]:
        return self._get_paginated(
            f"repos/{owner}/{repo}/pulls/{pull_number}/reviews",
            params={},
            page_size=page_size,
            max_pages=max_pages,
            max_results=max_results,
        )

    def get_contributors(
        self,
        owner: str,
        repo: str,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> list[dict[str, Any]]:
        return self._get_paginated(
            f"repos/{owner}/{repo}/contributors",
            params={"anon": "false"},
            page_size=page_size,
            max_pages=max_pages,
            max_results=max_results,
        )

    def _get_paginated(
        self,
        path: str,
        params: dict[str, str],
        page_size: int,
        max_pages: int,
        max_results: int,
    ) -> list[dict[str, Any]]:
        self._validate_pagination(page_size, max_pages, max_results)
        results: list[dict[str, Any]] = []
        next_url: str | None = path
        next_params: dict[str, str] | None = {
            **params,
            "per_page": str(page_size),
            "page": "1",
        }
        visited_urls: set[str] = set()
        pages_fetched = 0

        while next_url is not None and pages_fetched < max_pages:
            if next_url in visited_urls:
                raise GitHubPaginationError("GitHub pagination returned a repeated link")
            visited_urls.add(next_url)

            response = self._request("GET", next_url, params=next_params)
            values = self._json_list(response)
            remaining = max_results - len(results)
            results.extend(values[:remaining])
            pages_fetched += 1
            if len(results) >= max_results:
                break

            next_url = self._next_link(response.headers.get("Link"))
            next_params = None

        return results

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as error:
            raise GitHubTimeoutError("GitHub request timed out") from error
        except httpx.RequestError as error:
            raise GitHubRequestError("GitHub request failed") from error

        if response.status_code == 401:
            raise GitHubAuthenticationError("GitHub authentication failed")
        if (
            response.status_code == 403
            and response.headers.get("X-RateLimit-Remaining") == "0"
        ):
            raise GitHubRateLimitError("GitHub API rate limit exceeded")
        if response.is_error:
            raise GitHubHttpError(response.status_code)
        return response

    @staticmethod
    def _json_object(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as error:
            raise GitHubMalformedResponseError("GitHub returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise GitHubMalformedResponseError("GitHub response must be a JSON object")
        return payload

    @staticmethod
    def _json_list(response: httpx.Response) -> list[dict[str, Any]]:
        if response.status_code == 204:
            return []
        try:
            payload = response.json()
        except ValueError as error:
            raise GitHubMalformedResponseError("GitHub returned invalid JSON") from error
        if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
            raise GitHubMalformedResponseError(
                "GitHub response must be a JSON list of objects"
            )
        return payload

    @staticmethod
    def _next_link(link_header: str | None) -> str | None:
        if link_header is None:
            return None
        for link in link_header.split(","):
            match = re.match(r'\s*<([^>]+)>;\s*rel="([^"]+)"', link)
            if match and match.group(2) == "next":
                return match.group(1)
        if "rel=\"next\"" in link_header:
            raise GitHubPaginationError("GitHub pagination Link header is malformed")
        return None

    @staticmethod
    def _validate_pagination(
        page_size: int, max_pages: int, max_results: int
    ) -> None:
        if not 1 <= page_size <= 100:
            raise GitHubPaginationError("page_size must be between 1 and 100")
        if max_pages < 1 or max_results < 1:
            raise GitHubPaginationError("max_pages and max_results must be positive")

    @staticmethod
    def _iso_timestamp(value: datetime) -> str:
        return value.isoformat().replace("+00:00", "Z")
