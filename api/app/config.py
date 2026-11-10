from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (see api/.env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://veylith:veylith@localhost:5432/veylith"

    github_client_id: str = ""
    github_client_secret: str = ""

    session_secret: str = ""
    token_encryption_key: str = ""

    web_url: str = "http://localhost:3000"
    webhook_url: str = ""

    run_worker: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
