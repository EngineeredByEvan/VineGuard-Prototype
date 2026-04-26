from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class GatewaySettings(BaseModel):
    environment: Literal["development", "production", "test"] = "development"
    lora_mode: Literal["mock", "serial_json", "serial_binary", "chirpstack_mqtt"] = "mock"
    lora_serial_port: str = "/dev/ttyUSB0"
    lora_baud_rate: int = 115200

    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic: str = "vineguard/telemetry"
    mqtt_username: str = ""
    mqtt_password: str = ""

    ca_cert_path: Path | None = None
    client_cert_path: Path | None = None
    client_key_path: Path | None = None

    offline_cache_path: Path = Path("./data/offline-cache.jsonl")
    health_port: int = 8080


def load_settings() -> GatewaySettings:
    load_dotenv()
    return GatewaySettings()


@lru_cache
def get_settings() -> GatewaySettings:
    return load_settings()
