from __future__ import annotations

"""Configuration loading for the VineGuard edge gateway."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os


@dataclass(slots=True)
class Config:
    """Gateway runtime configuration loaded from environment variables."""

    gateway_id: str
    mqtt_host: str
    mqtt_port: int
    mqtt_username: Optional[str]
    mqtt_password: Optional[str]
    mqtt_use_tls: bool
    mqtt_ca_cert: Optional[Path]
    mqtt_client_cert: Optional[Path]
    mqtt_client_key: Optional[Path]
    mqtt_tls_insecure: bool
    queue_db_path: Path
    udp_listen_host: str
    udp_listen_port: int
    enable_udp_source: bool
    enable_lora_source: bool
    lora_force_simulation: bool
    health_port: int
    backoff_base: float
    backoff_max: float
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        env = os.getenv

        def _bool(name: str, default: bool = False) -> bool:
            value = env(name)
            if value is None:
                return default
            return value.strip().lower() in {"1", "true", "yes", "on"}

        def _path(name: str) -> Optional[Path]:
            value = env(name)
            if not value:
                return None
            return Path(value)

        queue_path = _path("QUEUE_DB_PATH") or Path(env("QUEUE_STORAGE_DIR", "./edge/gateway/data")) / "gateway_queue.db"
        queue_path.parent.mkdir(parents=True, exist_ok=True)

        mqtt_ca_cert = _path("MQTT_CA_CERT")
        mqtt_client_cert = _path("MQTT_CLIENT_CERT")
        mqtt_client_key = _path("MQTT_CLIENT_KEY")

        return cls(
            gateway_id=env("GATEWAY_ID", "vineguard-gateway"),
            mqtt_host=env("MQTT_HOST", "localhost"),
            mqtt_port=int(env("MQTT_PORT", "8883")),
            mqtt_username=env("MQTT_USERNAME"),
            mqtt_password=env("MQTT_PASSWORD"),
            mqtt_use_tls=_bool("MQTT_USE_TLS", True),
            mqtt_ca_cert=mqtt_ca_cert,
            mqtt_client_cert=mqtt_client_cert,
            mqtt_client_key=mqtt_client_key,
            mqtt_tls_insecure=_bool("MQTT_TLS_INSECURE", False),
            queue_db_path=queue_path,
            udp_listen_host=env("UDP_LISTEN_HOST", "0.0.0.0"),
            udp_listen_port=int(env("UDP_LISTEN_PORT", "1700")),
            enable_udp_source=_bool("ENABLE_UDP_SOURCE", True),
            enable_lora_source=_bool("ENABLE_LORA_SOURCE", True),
            lora_force_simulation=_bool("LORA_FORCE_SIMULATION", False),
            health_port=int(env("HEALTH_PORT", "8080")),
            backoff_base=float(env("MQTT_BACKOFF_BASE", "1.0")),
            backoff_max=float(env("MQTT_BACKOFF_MAX", "32.0")),
            log_level=env("LOG_LEVEL", "INFO"),
        )


__all__ = ["Config"]
