from __future__ import annotations

"""Core gateway orchestration logic."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from .config import Config
from .mqtt_client import CloudMqttClient
from .queue_store import PersistentQueue
from .sources.base import NodeKey, PacketSource
from .sources.lora import LoRaPacketSource
from .sources.udp import UDPJsonSource
from .telemetry_validator import TelemetryValidationError, TelemetryValidator


class Gateway:
    """Coordinates the ingress sources and MQTT egress."""

    def __init__(self, config: Config, queue: PersistentQueue, mqtt_client: CloudMqttClient, loop: asyncio.AbstractEventLoop) -> None:
        self.config = config
        self.queue = queue
        self.mqtt = mqtt_client
        self.loop = loop
        self.validator = TelemetryValidator()
        self.logger = logging.getLogger("gateway.core")
        self.sources: Dict[str, PacketSource] = {}
        self.node_sources: Dict[NodeKey, PacketSource] = {}
        self._flush_lock = asyncio.Lock()
        self._last_message_at: Optional[datetime] = None
        self._last_publish_success: Optional[datetime] = None
        self._mqtt_connected: bool = False

        self.mqtt.add_connection_listener(self._on_mqtt_connection_change)
        self.mqtt.subscribe("vineguard/+/+/+/cmd")

    async def start_sources(self) -> None:
        if self.config.enable_udp_source:
            udp_source = UDPJsonSource(
                host=self.config.udp_listen_host,
                port=self.config.udp_listen_port,
                message_callback=self.handle_message,
            )
            self.sources[udp_source.name] = udp_source
            await udp_source.start()

        if self.config.enable_lora_source:
            lora_source = LoRaPacketSource(
                message_callback=self.handle_message,
                force_simulation=self.config.lora_force_simulation,
            )
            self.sources[lora_source.name] = lora_source
            await lora_source.start()

    async def stop_sources(self) -> None:
        for source in list(self.sources.values()):
            try:
                await source.stop()
            except Exception:
                self.logger.exception("Failed to stop source", extra={"source": source.name})
        self.sources.clear()

    async def handle_message(self, source: PacketSource, payload: Dict, context: Dict) -> None:
        try:
            validated = self.validator.validate(payload)
        except TelemetryValidationError as exc:
            self.logger.warning(
                "Dropping telemetry due to validation failure",
                extra={"error": str(exc), "source": source.name},
            )
            return

        ingress_context = dict(context)
        ingress_context.setdefault('source', source.name)

        enriched = dict(validated)
        enriched.update(
            {
                'gatewayId': self.config.gateway_id,
                'receivedAt': datetime.now(timezone.utc).isoformat(),
                'ingress': ingress_context,
            }
        )
        topic = f"vineguard/{validated['orgId']}/{validated['siteId']}/{validated['nodeId']}/telemetry"
        message = json.dumps(enriched, separators=(",", ":"), sort_keys=True)

        key: NodeKey = (validated["orgId"], validated["siteId"], validated["nodeId"])
        source.register_node(key, context)
        self.node_sources[key] = source
        self._last_message_at = datetime.now(timezone.utc)

        if not self.mqtt.publish(topic, message):
            self.logger.warning("MQTT offline, queueing telemetry", extra={"topic": topic})
            self.queue.enqueue(topic, message)
        else:
            self._last_publish_success = datetime.now(timezone.utc)

    async def flush_queue(self) -> None:
        async with self._flush_lock:
            while self.mqtt.is_connected:
                batch = self.queue.get_batch()
                if not batch:
                    break
                success_ids = []
                for item in batch:
                    if self.mqtt.publish(item.topic, item.payload):
                        success_ids.append(item.id)
                    else:
                        self.logger.warning("Publish failed while flushing queue", extra={"id": item.id})
                        break
                if success_ids:
                    self.queue.remove(success_ids)
                    self._last_publish_success = datetime.now(timezone.utc)
                await asyncio.sleep(0)

    def handle_command(self, topic: str, payload: bytes) -> None:
        parts = topic.split("/")
        if len(parts) != 5:
            self.logger.warning("Unexpected command topic", extra={"topic": topic})
            return
        _, org_id, site_id, node_id, _ = parts
        key: NodeKey = (org_id, site_id, node_id)
        source = self.node_sources.get(key)
        if not source:
            self.logger.warning("No known source for command", extra={"topic": topic})
            return
        delivered = source.send_downlink(key, payload)
        if delivered:
            self.logger.info("Forwarded command to source", extra={"topic": topic, "source": source.name})
        else:
            self.logger.warning("Failed to forward command", extra={"topic": topic, "source": source.name})

    def _on_mqtt_connection_change(self, connected: bool) -> None:
        self.loop.call_soon_threadsafe(self._handle_connection_update, connected)

    def _handle_connection_update(self, connected: bool) -> None:
        self._mqtt_connected = connected
        if connected:
            asyncio.create_task(self.flush_queue())

    def build_health_status(self) -> Dict[str, Optional[str]]:
        queued = self.queue.count()
        return {
            "status": "ok" if self._mqtt_connected else "degraded",
            "mqttConnected": self._mqtt_connected,
            "queuedMessages": queued,
            "lastMessageReceived": self._last_message_at.isoformat() if self._last_message_at else None,
            "lastPublishSuccess": self._last_publish_success.isoformat() if self._last_publish_success else None,
        }


__all__ = ["Gateway"]
