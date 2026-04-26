from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from loguru import logger


@dataclass
class LoRaMessage:
    payload: dict


def decode_binary_payload(raw: bytes) -> dict:
    """Decode compact payload: >B H h h H H H B B H

    Fields: version, seq, soil_x10, temp_x10, humidity_x10, lux, batt_mV, tier, flags, crc
    """
    if len(raw) < 17:
        raise ValueError("binary payload too short")
    ver, seq, soil, temp, hum, lux, batt_mv, tier, flags, crc = struct.unpack(">B H h h H H H B B H", raw[:17])
    calc_crc = (sum(raw[:15]) & 0xFFFF)
    if crc != calc_crc:
        raise ValueError("crc mismatch")
    return {
        "schema_version": "1.0",
        "device_id": f"vg-bin-{seq:04d}",
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "tier": "precision_plus" if tier == 1 else "basic",
        "sensors": {
            "soil_moisture_pct": soil / 10,
            "soil_temp_c": temp / 10,
            "ambient_temp_c": temp / 10,
            "ambient_humidity_pct": hum / 10,
            "pressure_hpa": None,
            "light_lux": float(lux),
            "leaf_wetness_pct": 70.0 if flags & 0x1 else None,
        },
        "meta": {
            "battery_voltage": batt_mv / 1000,
            "battery_pct": None,
            "rssi": None,
            "snr": None,
            "sensor_ok": True,
        },
    }


def normalize_for_ingestor(payload: dict) -> dict:
    """Preserve compatibility with existing cloud parser.

    - Keep canonical v1 (`schema_version`, `device_id`, `sensors`, `meta`) if present.
    - Convert enhanced vineguard payloads by extracting same keys.
    - Convert flat legacy payload untouched.
    """
    if "schema_version" in payload and "sensors" in payload and "meta" in payload:
        return payload

    if "deviceId" in payload and "soilMoisture" in payload:
        return payload

    if "readings" in payload:
        r = payload["readings"]
        return {
            "schema_version": "1.0",
            "device_id": payload.get("deviceId") or payload.get("device_id"),
            "timestamp": payload.get("timestamp"),
            "tier": payload.get("nodeType", "basic"),
            "sensors": {
                "soil_moisture_pct": r.get("soilMoisturePercent", 0),
                "soil_temp_c": r.get("soilTempC", 0) or 0,
                "ambient_temp_c": r.get("ambientTempC", 0),
                "ambient_humidity_pct": r.get("ambientHumidityPercent", 0),
                "pressure_hpa": r.get("pressureHpa"),
                "light_lux": r.get("lightLux", 0),
                "leaf_wetness_pct": r.get("leafWetnessPercent"),
            },
            "meta": {
                "battery_voltage": r.get("batteryVoltage", 0),
                "battery_pct": r.get("batteryPercent"),
                "rssi": payload.get("radio", {}).get("rssi"),
                "snr": payload.get("radio", {}).get("snr"),
                "sensor_ok": True,
            },
            "vineguard": payload,
        }

    raise ValueError("unsupported payload format")


class LoRaInterface:
    def __init__(self, mode: str, serial_port: str, baud_rate: int) -> None:
        self.mode = mode
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self._serial = None

    def open(self) -> None:
        logger.info("lora_open", mode=self.mode, serial_port=self.serial_port, baud=self.baud_rate)
        if self.mode in {"serial_json", "serial_binary"}:
            import serial

            self._serial = serial.Serial(self.serial_port, self.baud_rate, timeout=1)

    def read_messages(self) -> Iterable[LoRaMessage]:
        if self.mode == "mock":
            raw = {
                "schema_version": "1.0",
                "device_id": "vg-node-001",
                "timestamp": int(datetime.now(timezone.utc).timestamp()),
                "tier": "basic",
                "sensors": {
                    "soil_moisture_pct": 28.2,
                    "soil_temp_c": 18.2,
                    "ambient_temp_c": 21.2,
                    "ambient_humidity_pct": 61.5,
                    "pressure_hpa": 1012.0,
                    "light_lux": 260.0,
                    "leaf_wetness_pct": None,
                },
                "meta": {"battery_voltage": 3.95, "battery_pct": 80, "rssi": -77, "snr": 8.3, "sensor_ok": True},
            }
            yield LoRaMessage(payload=raw)
            return

        if self._serial is None:
            return

        line = self._serial.readline()
        if not line:
            return

        try:
            if self.mode == "serial_json":
                payload = normalize_for_ingestor(json.loads(line.decode("utf-8", errors="ignore").strip()))
            else:
                payload = normalize_for_ingestor(decode_binary_payload(line.strip()))
            logger.info("decode_success")
            yield LoRaMessage(payload=payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("decode_failed", error=str(exc))


class OfflineCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, message: LoRaMessage) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message.payload) + "\n")
        logger.warning("cached_offline", path=str(self.path))

    def drain(self) -> list[LoRaMessage]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            messages = [LoRaMessage(payload=json.loads(line)) for line in handle if line.strip()]
        self.path.unlink()
        logger.info("cache_drained", count=len(messages))
        return messages
