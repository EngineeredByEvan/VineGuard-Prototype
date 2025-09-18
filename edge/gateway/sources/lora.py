from __future__ import annotations

"""LoRa packet source using SPI (with simulation fallback)."""

import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .base import PacketSource


class LoRaPacketSource(PacketSource):
    """LoRa packet source that falls back to simulation when hardware is absent."""

    def __init__(self, message_callback, force_simulation: bool = False) -> None:
        super().__init__("lora", message_callback)
        self.logger = logging.getLogger("gateway.lora")
        self._force_simulation = force_simulation
        self._task: Optional[asyncio.Task[None]] = None
        self._simulated = force_simulation
        self._hardware = None
        if not force_simulation:
            try:
                from lora import LoRa  # type: ignore

                self._hardware = LoRa()
                self._simulated = False
                self.logger.info("Initialized LoRa hardware interface")
            except Exception as exc:  # pragma: no cover - hardware path
                self._simulated = True
                self.logger.warning(
                    "LoRa hardware unavailable, using simulation",
                    extra={"error": str(exc)},
                )

    async def start(self) -> None:
        if self._simulated:
            self._task = asyncio.create_task(self._simulation_loop())
            self.logger.info("LoRa simulation started")
        else:  # pragma: no cover - hardware path
            self._task = asyncio.create_task(self._hardware_loop())
            self.logger.info("LoRa hardware loop started")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._hardware:  # pragma: no cover - hardware path
            try:
                self._hardware.close()
            except Exception:
                self.logger.exception("Failed to close LoRa hardware")

    async def _simulation_loop(self) -> None:
        nodes = ["lora-node-1", "lora-node-2"]
        while True:
            node = random.choice(nodes)
            payload = {
                "nodeId": node,
                "orgId": "sim-org",
                "siteId": "sim-site",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metrics": {
                    "temperature": round(random.uniform(10.0, 32.0), 2),
                    "humidity": round(random.uniform(40.0, 70.0), 2),
                },
            }
            context: Dict[str, Any] = {
                "transport": "lora",
                "rssi": random.randint(-110, -70),
                "snr": round(random.uniform(-12.0, 5.0), 2),
                "simulated": True,
            }
            await self._dispatch(payload, context)
            await asyncio.sleep(random.uniform(5.0, 10.0))

    async def _hardware_loop(self) -> None:  # pragma: no cover - hardware path
        assert self._hardware is not None
        while True:
            raw = self._hardware.recv()
            if not raw:
                await asyncio.sleep(0.1)
                continue
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                self.logger.warning("Received invalid LoRa payload", extra={"raw": raw})
                continue
            context: Dict[str, Any] = {"transport": "lora", "simulated": False}
            await self._dispatch(payload, context)

    def send_downlink(self, node_key, payload: bytes) -> bool:
        if self._simulated:
            try:
                decoded = payload.decode("utf-8")
            except Exception:
                decoded = str(payload)
            self.logger.info(
                "Simulated LoRa downlink", extra={"node": node_key, "payload": decoded}
            )
            return True
        if not self._hardware:  # pragma: no cover - hardware path
            self.logger.warning("LoRa hardware not initialised for downlink", extra={"node": node_key})
            return False
        try:
            self._hardware.send(payload)
            self.logger.info("LoRa downlink queued", extra={"node": node_key})
            return True
        except Exception:  # pragma: no cover - hardware path
            self.logger.exception("Failed to send LoRa downlink", extra={"node": node_key})
            return False


__all__ = ["LoRaPacketSource"]
