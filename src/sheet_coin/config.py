from functools import cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SHEET_COIN_", env_file=".env")

    auth_username: str
    auth_password: str
    port: int = 19877
    polling_interval: int = 45
    api_timeout: int = 60
    log_level: str = "INFO"


@cache
def get_settings() -> Settings:
    return Settings()
