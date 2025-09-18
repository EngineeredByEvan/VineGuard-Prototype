from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(..., alias="DATABASE_URL")

    mqtt_broker_host: str = Field(..., alias="MQTT_BROKER_HOST")
    mqtt_broker_port: int = Field(1883, alias="MQTT_BROKER_PORT")
    mqtt_username: str | None = Field(default=None, alias="MQTT_USERNAME")
    mqtt_password: str | None = Field(default=None, alias="MQTT_PASSWORD")
    mqtt_tls_enabled: bool = Field(False, alias="MQTT_TLS_ENABLED")

    telemetry_topic_filter: str = Field(..., alias="TELEMETRY_TOPIC_FILTER")
    status_topic_filter: str = Field(..., alias="STATUS_TOPIC_FILTER")
    cmd_topic_prefix: str = Field("vineguard", alias="CMD_TOPIC_PREFIX")

    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    access_token_expires_min: int = Field(15, alias="ACCESS_TOKEN_EXPIRES_MIN")
    refresh_token_expires_hours: int = Field(24 * 7, alias="REFRESH_TOKEN_EXPIRES_HOURS")

    api_host: str = Field("0.0.0.0", alias="API_HOST")
    api_port: int = Field(8000, alias="API_PORT")

    service_org_allowlist: List[str] = Field(default_factory=list, alias="SERVICE_ORG_ALLOWLIST")

    cors_allow_origins: List[AnyHttpUrl] | List[str] = Field(default_factory=list, alias="CORS_ALLOW_ORIGINS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
