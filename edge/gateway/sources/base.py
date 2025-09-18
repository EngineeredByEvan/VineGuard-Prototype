from __future__ import annotations

"""Base classes for gateway data sources."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Tuple

MessageCallback = Callable[["PacketSource", Dict[str, Any], Dict[str, Any]], Any]
NodeKey = Tuple[str, str, str]


class PacketSource(ABC):
    """Abstract base class for gateway ingress sources."""

    def __init__(self, name: str, message_callback: MessageCallback) -> None:
        self.name = name
        self._message_callback = message_callback

    @abstractmethod
    async def start(self) -> None:
        """Start receiving packets."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop receiving packets."""

    def register_node(self, node_key: NodeKey, context: Dict[str, Any]) -> None:
        """Allow sources to persist metadata for a node (no-op by default)."""

    def send_downlink(self, node_key: NodeKey, payload: bytes) -> bool:
        """Send a downlink payload to the specified node. Returns success."""
        return False

    async def _dispatch(self, payload: Dict[str, Any], context: Dict[str, Any]) -> None:
        awaitable = self._message_callback(self, payload, context)
        if hasattr(awaitable, "__await__"):
            await awaitable  # type: ignore[func-returns-value]


__all__ = ["PacketSource", "NodeKey", "MessageCallback"]
