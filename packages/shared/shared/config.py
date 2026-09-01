from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from the environment."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="TH_", extra="ignore")

    telegram_token: str = ""
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql://talent:hive@localhost:5432/talent_hive"


@lru_cache
def get_settings() -> Settings:
    return Settings()
