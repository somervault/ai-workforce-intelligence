from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # -------------------------
    # Application
    # -------------------------
    app_name: str
    app_version: str
    environment: str

    # -------------------------
    # Database
    # -------------------------
    database_host: str
    database_port: int
    database_name: str
    database_user: str
    database_password: str

    # -------------------------
    # Security
    # -------------------------
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    # -------------------------
    # AI
    # -------------------------
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # -------------------------
    # Jira Cloud
    # -------------------------
    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    jira_request_timeout_seconds: float = 10.0

    # -------------------------
    # GitHub
    # -------------------------
    github_api_base_url: str = "https://api.github.com"
    github_token: str = ""
    github_org: str = ""
    github_request_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
