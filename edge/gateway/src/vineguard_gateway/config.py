from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, HttpUrl


class GatewaySettings(BaseModel):
    environment: Literal["development", "production", "test"] = Field(
        default="development",
        description="Runtime environment identifier",
    )
    lora_serial_port: str = Field(..., description="Serial port attached to the LoRa concentrator")
    lora_baud_rate: int = Field(default=9600, description="Baud rate for the LoRa UART module")
    mqtt_host: str = Field(..., description="MQTT broker hostname")
    mqtt_port: int = Field(default=8883, description="MQTT broker TLS port")
    mqtt_topic: str = Field(default="vineguard/telemetry", description="Telemetry topic")
    mqtt_username: str = Field(..., description="MQTT username with publish rights")
    mqtt_password: str = Field(..., description="MQTT password")
    ca_cert_path: Path = Field(..., description="Path to CA certificate for TLS validation")
    client_cert_path: Path | None = Field(default=None, description="Client certificate if mutual TLS is enabled")
    client_key_path: Path | None = Field(default=None, description="Client key for mutual TLS")
    offline_cache_path: Path = Field(
        default=Path("./data/offline-cache.jsonl"),
        description="Where to buffer telemetry when connectivity is lost",
    )
    health_port: int = Field(default=8080, description="HTTP port for health probes")
    ota_control_url: HttpUrl = Field(
        default="https://cloud.vineguard.local/api/ota",
        description="Cloud OTA coordination endpoint",
    )


def load_settings() -> GatewaySettings:
    load_dotenv()
    return GatewaySettings()


@lru_cache
def get_settings() -> GatewaySettings:
    return load_settings()
