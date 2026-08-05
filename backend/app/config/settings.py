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

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
