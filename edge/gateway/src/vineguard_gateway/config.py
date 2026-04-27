from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, HttpUrl


class GatewaySettings(BaseModel):
    environment: Literal["development", "production", "test"] = Field(
        default="development",
    )

    # ─── LoRa / radio mode ───────────────────────────────────────────────────
    # mock           : generate synthetic payloads (development / CI)
    # serial_json    : read VGPAYLOAD:<json> lines from USB serial
    # serial_binary  : read raw VGPP-1 binary frames from USB serial
    # chirpstack_mqtt: subscribe to ChirpStack MQTT application topic
    lora_mode: Literal["mock", "serial_json", "serial_binary", "chirpstack_mqtt"] = Field(
        default="mock",
        description="LoRa receive mode",
    )
    lora_serial_port: str = Field(
        default="/dev/ttyUSB0",
        description="Serial port for serial_json / serial_binary modes",
    )
    lora_baud_rate: int = Field(
        default=115200,
        description="Baud rate; must match firmware monitor_speed (default 115200)",
    )

    # ─── MQTT ────────────────────────────────────────────────────────────────
    mqtt_host: str = Field(..., description="MQTT broker hostname")
    mqtt_port: int = Field(default=8883, description="MQTT broker port (TLS)")
    mqtt_topic: str = Field(default="vineguard/telemetry", description="Telemetry publish topic")
    mqtt_username: str = Field(..., description="MQTT publish-only username")
    mqtt_password: str = Field(..., description="MQTT password")

    # ─── TLS ─────────────────────────────────────────────────────────────────
    ca_cert_path: Path = Field(..., description="CA certificate for TLS broker verification")
    client_cert_path: Path | None = Field(default=None, description="Client cert for mTLS")
    client_key_path: Path | None = Field(default=None, description="Client key for mTLS")

    # ─── Offline cache ────────────────────────────────────────────────────────
    offline_cache_path: Path = Field(
        default=Path("./data/offline-cache.jsonl"),
        description="JSONL file for messages buffered during connectivity loss",
    )

    # ─── Health / OTA ────────────────────────────────────────────────────────
    health_port: int = Field(default=8080, description="HTTP health probe port")
    ota_control_url: HttpUrl = Field(
        default="https://cloud.vineguard.local/api/ota",
        description="Cloud OTA endpoint (unused in MVP)",
    )

    # ─── Gateway identity ─────────────────────────────────────────────────────
    gateway_id: str = Field(default="vg-gw-001", description="Gateway ID injected into payloads")

    model_config = {"populate_by_name": True}


def load_settings() -> GatewaySettings:
    load_dotenv()
    return GatewaySettings()


@lru_cache
def get_settings() -> GatewaySettings:
    return load_settings()
