from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecuritySettings(BaseModel):
    api_key: str = Field(..., min_length=16)
    jwt_secret: str = Field(..., min_length=32)
    jwt_algorithm: Literal["HS256", "HS512"] = "HS256"
    jwt_ttl_seconds: int = Field(default=3600, ge=300)


class DatabaseSettings(BaseModel):
    dsn: str = Field(..., description="Asyncpg DSN for TimescaleDB")
    min_size: int = Field(default=1, ge=1)
    max_size: int = Field(default=10, ge=1)


class RedisSettings(BaseModel):
    url: str = Field(default="redis://redis:6379/0")
    telemetry_channel: str = Field(default="telemetry-stream")


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="API_", env_nested_delimiter="__")

    environment: Literal["development", "production", "test"] = "development"
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    security: SecuritySettings
    database: DatabaseSettings
    redis: RedisSettings = Field(default_factory=RedisSettings)


@lru_cache
def get_settings() -> ApiSettings:
    return ApiSettings()  # type: ignore[arg-type]
