from datetime import datetime
from typing import Any

from app.config.settings import settings
from app.integrations.github_client import GitHubClient, GitHubMalformedResponseError
from app.integrations.github_schemas import (
    GitHubCommitDTO,
    GitHubContributorDTO,
    GitHubPullRequestDTO,
    GitHubPullRequestReviewDTO,
    GitHubRepositoryDTO,
    GitHubUserDTO,
)


class GitHubService:
    """Application-facing, read-only GitHub integration service."""

    def __init__(self, client: GitHubClient | None = None):
        self.client = client or GitHubClient(
            api_base_url=settings.github_api_base_url,
            token=settings.github_token,
            org=settings.github_org,
            timeout_seconds=settings.github_request_timeout_seconds,
        )

    def get_authenticated_user(self) -> GitHubUserDTO:
        return self._user_from_raw(self.client.get_authenticated_user())

    def verify_user_id(self, user_id: str) -> GitHubUserDTO:
        user = self._user_from_raw(self.client.get_user_by_id(user_id))
        if str(user.id) != user_id:
            raise GitHubMalformedResponseError("GitHub returned a different user ID")
        return user

    def get_repositories(self, **pagination: int) -> list[GitHubRepositoryDTO]:
        return [
            self._repository_from_raw(repository)
            for repository in self.client.get_repositories(**pagination)
        ]

    def get_commits(
        self,
        owner: str,
        repo: str,
        since: datetime | None = None,
        until: datetime | None = None,
        **pagination: int,
    ) -> list[GitHubCommitDTO]:
        return [
            self._commit_from_raw(commit)
            for commit in self.client.get_commits(owner, repo, since, until, **pagination)
        ]

    def get_pull_requests(
        self, owner: str, repo: str, **pagination: int
    ) -> list[GitHubPullRequestDTO]:
        return [
            self._pull_request_from_raw(pull_request)
            for pull_request in self.client.get_pull_requests(owner, repo, **pagination)
        ]

    def get_pull_request_reviews(
        self, owner: str, repo: str, pull_number: int, **pagination: int
    ) -> list[GitHubPullRequestReviewDTO]:
        return [
            self._review_from_raw(review)
            for review in self.client.get_pull_request_reviews(owner, repo, pull_number, **pagination)
        ]

    def get_contributors(self, owner: str, repo: str, **pagination: int) -> list[GitHubContributorDTO]:
        return [
            self._contributor_from_raw(contributor)
            for contributor in self.client.get_contributors(owner, repo, **pagination)
        ]

    @staticmethod
    def _user_from_raw(user: dict[str, Any]) -> GitHubUserDTO:
        return GitHubUserDTO(
            id=GitHubService._required_int(user, "id"),
            login=GitHubService._required_string(user, "login"),
        )

    @staticmethod
    def _repository_from_raw(repository: dict[str, Any]) -> GitHubRepositoryDTO:
        owner = repository.get("owner")
        if not isinstance(owner, dict):
            raise GitHubMalformedResponseError("Repository response is missing owner")
        return GitHubRepositoryDTO(
            id=GitHubService._required_int(repository, "id"),
            owner_login=GitHubService._required_string(owner, "login"),
            name=GitHubService._required_string(repository, "name"),
            full_name=GitHubService._required_string(repository, "full_name"),
            private=GitHubService._required_bool(repository, "private"),
            archived=GitHubService._required_bool(repository, "archived"),
            default_branch=GitHubService._optional_string(repository, "default_branch"),
            pushed_at=GitHubService._optional_string(repository, "pushed_at"),
            updated_at=GitHubService._optional_string(repository, "updated_at"),
        )

    @staticmethod
    def _commit_from_raw(commit: dict[str, Any]) -> GitHubCommitDTO:
        commit_data = commit.get("commit")
        if not isinstance(commit_data, dict):
            raise GitHubMalformedResponseError("Commit response is missing commit data")
        author = commit.get("author")
        committer = commit.get("committer")
        if author is not None and not isinstance(author, dict):
            raise GitHubMalformedResponseError("Commit author must be an object or null")
        if committer is not None and not isinstance(committer, dict):
            raise GitHubMalformedResponseError("Commit committer must be an object or null")
        commit_author = commit_data.get("author")
        commit_committer = commit_data.get("committer")
        if commit_author is not None and not isinstance(commit_author, dict):
            raise GitHubMalformedResponseError("Commit author data must be an object or null")
        if commit_committer is not None and not isinstance(commit_committer, dict):
            raise GitHubMalformedResponseError("Commit committer data must be an object or null")
        return GitHubCommitDTO(
            sha=GitHubService._required_string(commit, "sha"),
            author_id=GitHubService._optional_int(author, "id") if author else None,
            author_login=GitHubService._optional_string(author, "login") if author else None,
            committer_id=(GitHubService._optional_int(committer, "id") if committer else None),
            committer_login=(
                GitHubService._optional_string(committer, "login") if committer else None
            ),
            authored_at=(
                GitHubService._optional_string(commit_author, "date")
                if commit_author
                else None
            ),
            committed_at=(
                GitHubService._optional_string(commit_committer, "date")
                if commit_committer
                else None
            ),
        )

    @staticmethod
    def _pull_request_from_raw(pull_request: dict[str, Any]) -> GitHubPullRequestDTO:
        user = pull_request.get("user")
        if user is not None and not isinstance(user, dict):
            raise GitHubMalformedResponseError("Pull request user must be an object or null")
        return GitHubPullRequestDTO(
            number=GitHubService._required_int(pull_request, "number"),
            title=GitHubService._required_string(pull_request, "title"),
            state=GitHubService._required_string(pull_request, "state"),
            draft=GitHubService._required_bool(pull_request, "draft"),
            author_id=GitHubService._optional_int(user, "id") if user else None,
            author_login=GitHubService._optional_string(user, "login") if user else None,
            created_at=GitHubService._optional_string(pull_request, "created_at"),
            updated_at=GitHubService._optional_string(pull_request, "updated_at"),
            merged_at=GitHubService._optional_string(pull_request, "merged_at"),
        )

    @staticmethod
    def _review_from_raw(review: dict[str, Any]) -> GitHubPullRequestReviewDTO:
        user = review.get("user")
        if user is not None and not isinstance(user, dict):
            raise GitHubMalformedResponseError("Review user must be an object or null")
        return GitHubPullRequestReviewDTO(
            id=GitHubService._required_int(review, "id"),
            state=GitHubService._required_string(review, "state"),
            reviewer_id=GitHubService._optional_int(user, "id") if user else None,
            reviewer_login=GitHubService._optional_string(user, "login") if user else None,
            submitted_at=GitHubService._optional_string(review, "submitted_at"),
        )

    @staticmethod
    def _contributor_from_raw(contributor: dict[str, Any]) -> GitHubContributorDTO:
        return GitHubContributorDTO(
            id=GitHubService._required_int(contributor, "id"),
            login=GitHubService._required_string(contributor, "login"),
            contributions=GitHubService._required_int(contributor, "contributions"),
        )

    @staticmethod
    def _required_string(value: dict[str, Any], field_name: str) -> str:
        result = value.get(field_name)
        if not isinstance(result, str) or not result:
            raise GitHubMalformedResponseError(
                f"GitHub response field '{field_name}' must be a non-empty string"
            )
        return result

    @staticmethod
    def _optional_string(value: dict[str, Any], field_name: str) -> str | None:
        result = value.get(field_name)
        if result is None:
            return None
        if not isinstance(result, str):
            raise GitHubMalformedResponseError(
                f"GitHub response field '{field_name}' must be a string or null"
            )
        return result

    @staticmethod
    def _required_int(value: dict[str, Any], field_name: str) -> int:
        result = value.get(field_name)
        if not isinstance(result, int) or isinstance(result, bool):
            raise GitHubMalformedResponseError(
                f"GitHub response field '{field_name}' must be an integer"
            )
        return result

    @staticmethod
    def _optional_int(value: dict[str, Any], field_name: str) -> int | None:
        result = value.get(field_name)
        if result is None:
            return None
        if not isinstance(result, int) or isinstance(result, bool):
            raise GitHubMalformedResponseError(
                f"GitHub response field '{field_name}' must be an integer or null"
            )
        return result

    @staticmethod
    def _required_bool(value: dict[str, Any], field_name: str) -> bool:
        result = value.get(field_name)
        if not isinstance(result, bool):
            raise GitHubMalformedResponseError(
                f"GitHub response field '{field_name}' must be a boolean"
            )
        return result
