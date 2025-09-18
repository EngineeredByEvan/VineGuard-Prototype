from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    dsn: str


class RedisSettings(BaseModel):
    url: str = "redis://redis:6379/0"
    telemetry_channel: str = "telemetry-stream"


class AnalyticsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ANALYTICS_", env_nested_delimiter="__")

    database: DatabaseSettings
    redis: RedisSettings = RedisSettings()
    polling_interval_seconds: int = 300


@lru_cache
def get_settings() -> AnalyticsSettings:
    return AnalyticsSettings()  # type: ignore[arg-type]
