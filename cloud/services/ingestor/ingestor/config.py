from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MqttSettings(BaseModel):
    host: str
    port: int = 8883
    username: str
    password: str
    topic: str = "vineguard/telemetry"
    tls_ca_path: str
    client_cert_path: str | None = None
    client_key_path: str | None = None


class DatabaseSettings(BaseModel):
    dsn: str


class RedisSettings(BaseModel):
    url: str = "redis://redis:6379/0"
    telemetry_channel: str = "telemetry-stream"


class IngestorSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="INGESTOR_", env_nested_delimiter="__")

    mqtt: MqttSettings
    database: DatabaseSettings
    redis: RedisSettings = Field(default_factory=RedisSettings)


@lru_cache
def get_settings() -> IngestorSettings:
    return IngestorSettings()  # type: ignore[arg-type]
