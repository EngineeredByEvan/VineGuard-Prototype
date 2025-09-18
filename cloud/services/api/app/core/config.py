from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    mqtt_host: str = Field(..., env="MQTT_HOST")
    mqtt_port: int = Field(1883, env="MQTT_PORT")
    mqtt_username: str | None = Field(None, env="MQTT_USERNAME")
    mqtt_password: str | None = Field(None, env="MQTT_PASSWORD")

    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expires_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRES_MINUTES")
    refresh_token_expires_minutes: int = Field(60 * 24 * 7, env="REFRESH_TOKEN_EXPIRES_MINUTES")

    api_base_url: str = Field("http://localhost:8000", env="API_BASE_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
