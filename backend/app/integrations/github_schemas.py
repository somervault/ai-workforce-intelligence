from datetime import datetime

from pydantic import BaseModel


class GitHubUserDTO(BaseModel):
    id: int
    login: str


class GitHubRepositoryDTO(BaseModel):
    id: int
    owner_login: str
    name: str
    full_name: str
    private: bool
    archived: bool
    default_branch: str | None = None
    pushed_at: datetime | None = None
    updated_at: datetime | None = None


class GitHubCommitDTO(BaseModel):
    sha: str
    author_login: str | None = None
    committer_login: str | None = None
    authored_at: datetime | None = None
    committed_at: datetime | None = None


class GitHubPullRequestDTO(BaseModel):
    number: int
    title: str
    state: str
    draft: bool
    author_login: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    merged_at: datetime | None = None


class GitHubPullRequestReviewDTO(BaseModel):
    id: int
    state: str
    reviewer_login: str | None = None
    submitted_at: datetime | None = None


class GitHubContributorDTO(BaseModel):
    id: int
    login: str
    contributions: int
