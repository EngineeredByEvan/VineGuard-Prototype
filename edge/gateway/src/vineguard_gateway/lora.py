"""
lora.py — LoRa receive interface for the VineGuard gateway.

Four modes controlled by LORA_MODE environment variable:

  mock           : Yield synthetic V1 payloads (CI, development, no hardware)
  serial_json    : Read VGPAYLOAD:<json> lines from USB serial (LoRa P2P node)
  serial_binary  : Read raw VGPP-1 binary frames from USB serial (future)
  chirpstack_mqtt: Subscribe to ChirpStack MQTT application topic (LoRaWAN)

All modes yield LoRaMessage objects with payload already decoded to V1 dict
format, ready for MQTT publish.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Iterable

from loguru import logger

from .config import GatewaySettings
from .decoder import PayloadDecodeError, decode_auto


@dataclass
class LoRaMessage:
    payload: dict
    rssi: int | None = None
    snr: float | None = None
    raw: bytes | str | None = field(default=None, repr=False)


# ─── OfflineCache ─────────────────────────────────────────────────────────────

class OfflineCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, message: LoRaMessage) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message.payload) + "\n")
        logger.warning("Cached message offline (device={})", message.payload.get("device_id"))

    def drain(self) -> list[LoRaMessage]:
        if not self.path.exists():
            return []
        messages = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    try:
                        messages.append(LoRaMessage(payload=json.loads(line)))
                    except json.JSONDecodeError as exc:
                        logger.warning("Skipping malformed cache line: {}", exc)
        self.path.unlink()
        if messages:
            logger.info("Drained {} cached messages from {}", len(messages), self.path)
        return messages


# ─── LoRa interface factory ────────────────────────────────────────────────────

class LoRaInterface:
    """Public interface; delegates to mode-specific implementation."""

    def __init__(self, settings: GatewaySettings) -> None:
        self._settings = settings
        self._impl = _build_impl(settings)

    def open(self) -> None:
        self._impl.open()

    def read_messages(self) -> Iterable[LoRaMessage]:
        return self._impl.read_messages()


def _build_impl(settings: GatewaySettings):
    mode = settings.lora_mode
    if mode == "mock":
        return _MockLoRa(settings)
    if mode == "serial_json":
        return _SerialJsonLoRa(settings)
    if mode == "serial_binary":
        return _SerialBinaryLoRa(settings)
    if mode == "chirpstack_mqtt":
        return _ChirpStackMqttLoRa(settings)
    raise ValueError(f"Unknown LORA_MODE: {mode}")


# ─── Mock (development / CI) ──────────────────────────────────────────────────

class _MockLoRa:
    _SCENARIOS = [
        {
            # healthy basic node
            "schema_version": "1.0",
            "device_id":      "vg-node-001",
            "tier":           "basic",
            "sensors": {
                "soil_moisture_pct": 28.4,
                "soil_temp_c":       None,
                "ambient_temp_c":    21.3,
                "ambient_humidity_pct": 63.2,
                "pressure_hpa":      1007.2,
                "light_lux":         24500.0,
                "leaf_wetness_pct":  None,
            },
            "meta": {
                "battery_voltage": 11.5,
                "battery_pct":     65,
                "rssi":            -78,
                "snr":             9.1,
                "sensor_ok":       True,
                "solar_voltage":   None,
            },
        },
        {
            # low moisture alert scenario
            "schema_version": "1.0",
            "device_id":      "vg-node-002",
            "tier":           "basic",
            "sensors": {
                "soil_moisture_pct": 11.2,
                "soil_temp_c":       None,
                "ambient_temp_c":    24.8,
                "ambient_humidity_pct": 45.0,
                "pressure_hpa":      1010.0,
                "light_lux":         35000.0,
                "leaf_wetness_pct":  None,
            },
            "meta": {
                "battery_voltage": 10.8,
                "battery_pct":     45,
                "rssi":            -85,
                "snr":             6.5,
                "sensor_ok":       True,
                "solar_voltage":   13.2,
            },
        },
        {
            # precision+ mildew risk
            "schema_version": "1.0",
            "device_id":      "vg-node-003",
            "tier":           "precision_plus",
            "sensors": {
                "soil_moisture_pct": 38.5,
                "soil_temp_c":       None,
                "ambient_temp_c":    19.2,
                "ambient_humidity_pct": 88.0,
                "pressure_hpa":      1003.5,
                "light_lux":         8200.0,
                "leaf_wetness_pct":  72.0,
            },
            "meta": {
                "battery_voltage": 11.9,
                "battery_pct":     78,
                "rssi":            -70,
                "snr":             11.2,
                "sensor_ok":       True,
                "solar_voltage":   None,
            },
        },
    ]

    def __init__(self, settings: GatewaySettings) -> None:
        self._settings  = settings
        self._idx       = 0

    def open(self) -> None:
        logger.info("LoRa mode: mock (synthetic payloads)")

    def read_messages(self) -> list[LoRaMessage]:
        scenario = dict(self._SCENARIOS[self._idx % len(self._SCENARIOS)])
        self._idx += 1
        # Add live timestamp
        scenario["timestamp"] = int(time.time())
        scenario["gateway_id"] = self._settings.gateway_id
        msg = LoRaMessage(
            payload=scenario,
            rssi=scenario["meta"].get("rssi"),
            snr=scenario["meta"].get("snr"),
        )
        logger.debug("Mock: generated payload for {}", scenario["device_id"])
        return [msg]


# ─── Serial JSON (LoRa P2P VGPAYLOAD: lines) ─────────────────────────────────

class _SerialJsonLoRa:
    def __init__(self, settings: GatewaySettings) -> None:
        self._settings = settings
        self._serial = None

    def open(self) -> None:
        try:
            import serial  # type: ignore[import]
            self._serial = serial.Serial(
                self._settings.lora_serial_port,
                self._settings.lora_baud_rate,
                timeout=2.0,
            )
            logger.info("LoRa mode: serial_json on {} @ {} baud",
                        self._settings.lora_serial_port, self._settings.lora_baud_rate)
        except ImportError:
            logger.error("pyserial not installed. Run: pip install pyserial")
            self._serial = None
        except Exception as exc:
            logger.error("Cannot open serial port {}: {}", self._settings.lora_serial_port, exc)
            self._serial = None

    def read_messages(self) -> list[LoRaMessage]:
        if self._serial is None:
            return []
        messages = []
        try:
            while self._serial.in_waiting:
                raw_line = self._serial.readline().decode("utf-8", errors="replace").strip()
                if not raw_line:
                    continue
                logger.debug("Serial RX: {}", raw_line[:120])
                try:
                    payload = decode_auto(raw_line, gateway_id=self._settings.gateway_id)
                    msg = LoRaMessage(payload=payload, raw=raw_line)
                    # Annotate RSSI/SNR if the firmware printed them separately
                    # (future: parse RSSI:<val> SNR:<val> lines)
                    messages.append(msg)
                    logger.info("Decoded serial_json payload from {}", payload.get("device_id"))
                except PayloadDecodeError as exc:
                    logger.warning("Decode error (skipping): {}", exc)
        except Exception as exc:
            logger.error("Serial read error: {}", exc)
        return messages


# ─── Serial Binary (VGPP-1) ───────────────────────────────────────────────────

class _SerialBinaryLoRa:
    """
    Read raw VGPP-1 binary frames from serial.
    Frame detection: wait for 0xA1 start byte, read fixed-length frame.
    TODO: If variable-length framing is needed, add a length prefix.
    """
    FRAME_MIN = 22
    FRAME_MAX = 25

    def __init__(self, settings: GatewaySettings) -> None:
        self._settings = settings
        self._serial = None

    def open(self) -> None:
        try:
            import serial  # type: ignore[import]
            self._serial = serial.Serial(
                self._settings.lora_serial_port,
                self._settings.lora_baud_rate,
                timeout=2.0,
            )
            logger.info("LoRa mode: serial_binary on {} @ {} baud",
                        self._settings.lora_serial_port, self._settings.lora_baud_rate)
        except Exception as exc:
            logger.error("Cannot open serial port: {}", exc)
            self._serial = None

    def read_messages(self) -> list[LoRaMessage]:
        if self._serial is None:
            return []
        messages = []
        try:
            while self._serial.in_waiting >= self.FRAME_MIN:
                # Scan for start byte
                b = self._serial.read(1)
                if b[0] != 0xA1:
                    continue
                # Read remainder (max frame - 1 start byte)
                rest = self._serial.read(self.FRAME_MAX - 1)
                frame = b + rest
                try:
                    payload = decode_auto(frame, gateway_id=self._settings.gateway_id)
                    messages.append(LoRaMessage(payload=payload, raw=frame))
                    logger.info("Decoded binary frame ({} bytes)", len(frame))
                except PayloadDecodeError as exc:
                    logger.warning("Binary decode error: {}", exc)
        except Exception as exc:
            logger.error("Serial binary read error: {}", exc)
        return messages


# ─── ChirpStack MQTT (LoRaWAN via ChirpStack application server) ──────────────

class _ChirpStackMqttLoRa:
    """
    Subscribe to ChirpStack's application MQTT topic and decode uplink payloads.

    ChirpStack topic format (v4):
        application/{application_id}/device/{dev_eui}/event/up

    The payload codec configured in ChirpStack should emit VGPP-1 binary or
    the compact JSON format.  If no codec is configured, raw base64 data is
    in the `data` field.

    TODO: This is a stub.  Configure the ChirpStack application ID and
    device profile in your environment.  See docs/GATEWAY_INTEGRATION.md.
    """

    def __init__(self, settings: GatewaySettings) -> None:
        self._settings = settings
        self._pending: list[LoRaMessage] = []

    def open(self) -> None:
        logger.warning(
            "LoRa mode: chirpstack_mqtt — stub implementation. "
            "Configure ChirpStack MQTT broker and topic in environment. "
            "See docs/GATEWAY_INTEGRATION.md."
        )
        # TODO: connect to ChirpStack MQTT and subscribe to uplink topic

    def read_messages(self) -> list[LoRaMessage]:
        # TODO: return messages received from ChirpStack subscription
        messages = self._pending[:]
        self._pending.clear()
        return messages
