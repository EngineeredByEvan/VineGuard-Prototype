from __future__ import annotations

"""UDP JSON packet source for lab testing."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from .base import NodeKey, PacketSource


class _UDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, source: "UDPJsonSource") -> None:
        self._source = source

    def datagram_received(self, data: bytes, addr) -> None:  # type: ignore[override]
        asyncio.create_task(self._source._handle_datagram(data, addr))

    def error_received(self, exc: Exception) -> None:  # type: ignore[override]
        self._source.logger.error("UDP error", extra={"error": str(exc)})


class UDPJsonSource(PacketSource):
    """Packet source that consumes JSON payloads over UDP."""

    def __init__(self, host: str, port: int, message_callback) -> None:
        super().__init__("udp", message_callback)
        self._host = host
        self._port = port
        self._transport: Optional[asyncio.transports.DatagramTransport] = None
        self._node_addresses: Dict[NodeKey, Any] = {}
        self.logger = logging.getLogger("gateway.udp")

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: _UDPProtocol(self),
            local_addr=(self._host, self._port),
        )
        self.logger.info("UDP source started", extra={"host": self._host, "port": self._port})

    async def stop(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
            self.logger.info("UDP source stopped")

    async def _handle_datagram(self, data: bytes, addr) -> None:
        try:
            payload = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            self.logger.warning("Dropping invalid JSON payload", extra={"remote": addr})
            return
        context: Dict[str, Any] = {"transport": "udp", "remote": addr}
        await self._dispatch(payload, context)

    def register_node(self, node_key: NodeKey, context: Dict[str, Any]) -> None:
        remote = context.get("remote")
        if remote:
            self._node_addresses[node_key] = remote

    def send_downlink(self, node_key: NodeKey, payload: bytes) -> bool:
        if self._transport is None:
            self.logger.warning("UDP transport not ready for downlink", extra={"node": node_key})
            return False
        remote = self._node_addresses.get(node_key)
        if not remote:
            self.logger.warning("No UDP endpoint known for node", extra={"node": node_key})
            return False
        self._transport.sendto(payload, remote)
        self.logger.info("Sent UDP downlink", extra={"node": node_key, "remote": remote})
        return True


__all__ = ["UDPJsonSource"]
