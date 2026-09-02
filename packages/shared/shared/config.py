from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from the environment."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="TH_", extra="ignore")

    telegram_token: str = ""
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql://talent:hive@localhost:5432/talent_hive"

    # AI provider credentials. Left empty means the provider is unavailable.
    groq_api_key: str = ""
    google_ai_api_key: str = ""

    # Provider selection per artifact type. Values are provider ids
    # ("groq" | "google"). "auto" lets the router pick the first configured one.
    cover_letter_provider: str = "auto"
    resume_provider: str = "auto"
    job_description_provider: str = "auto"


@lru_cache
def get_settings() -> Settings:
    return Settings()
