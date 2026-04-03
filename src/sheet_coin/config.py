"""Application settings loaded from environment variables."""

from functools import cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the sheet-coin service."""

    model_config = SettingsConfigDict(env_prefix="SHEET_COIN_", env_file=".env")

    auth_username: str
    auth_password: str
    port: int = 19877
    polling_interval: int = 45
    api_timeout: int = 60
    log_level: str = "INFO"


@cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
