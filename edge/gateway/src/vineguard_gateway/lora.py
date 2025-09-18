from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from loguru import logger


@dataclass
class LoRaMessage:
    payload: dict


class LoRaInterface:
    """Placeholder for a concentrator driver."""

    def __init__(self, serial_port: str, baud_rate: int) -> None:
        self.serial_port = serial_port
        self.baud_rate = baud_rate

    def open(self) -> None:
        logger.info("Opening LoRa interface on {} @ {} baud", self.serial_port, self.baud_rate)
        # TODO: initialise Radio concentrator using pyserial

    def read_messages(self) -> Iterable[LoRaMessage]:
        # TODO: implement real decoding
        logger.debug("Reading from mock LoRa interface")
        yield LoRaMessage(payload={
            "deviceId": "vineguard-node-001",
            "soilMoisture": 57.2,
            "soilTempC": 18.5,
            "ambientTempC": 21.3,
            "ambientHumidity": 63.2,
            "lightLux": 245.0,
            "batteryVoltage": 3.97,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


class OfflineCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, message: LoRaMessage) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message.payload) + "\n")
        logger.warning("Cached message offline due to connectivity issue")

    def drain(self) -> list[LoRaMessage]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            messages = [LoRaMessage(payload=json.loads(line)) for line in handle if line.strip()]
        self.path.unlink()
        logger.info("Drained {} cached messages", len(messages))
        return messages
