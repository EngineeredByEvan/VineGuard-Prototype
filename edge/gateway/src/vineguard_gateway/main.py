"""
main.py — VineGuard LoRa-to-MQTT gateway process.

Reads telemetry from a LoRa interface (mock, serial, or ChirpStack MQTT),
decodes payloads into the V1 format, validates them, and publishes to the
MQTT broker with QoS 1.  Falls back to an offline JSONL cache when the
broker is unreachable.
"""

from __future__ import annotations

import signal
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Thread
from time import sleep

from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import GatewaySettings, get_settings
from .decoder import validate_v1
from .lora import LoRaInterface, LoRaMessage, OfflineCache
from .mqtt_client import MqttPublisher

_shutdown_event = Event()


# ─── Health endpoint ──────────────────────────────────────────────────────────

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","service":"vineguard-gateway"}')
        else:
            self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def start_health_server(settings: GatewaySettings) -> HTTPServer:
    server = HTTPServer(("0.0.0.0", settings.health_port), HealthHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Health endpoint listening on :{}/healthz", settings.health_port)
    return server


# ─── Publish with retry ────────────────────────────────────────────────────────

@retry(
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(ConnectionError),
)
def _publish_with_retry(publisher: MqttPublisher, messages: list[LoRaMessage]) -> None:
    publisher.publish_messages(messages)


# ─── Process loop ─────────────────────────────────────────────────────────────

def _process_messages(
    messages: list[LoRaMessage],
    publisher: MqttPublisher,
    cache: OfflineCache,
) -> None:
    valid = []
    for msg in messages:
        ok, reason = validate_v1(msg.payload)
        if ok:
            valid.append(msg)
            logger.info(
                "Payload validated: device={} tier={} soil={} T={}",
                msg.payload.get("device_id"),
                msg.payload.get("tier"),
                msg.payload.get("sensors", {}).get("soil_moisture_pct"),
                msg.payload.get("sensors", {}).get("ambient_temp_c"),
            )
        else:
            logger.warning("Payload validation failed ({}), dropping: device={}",
                           reason, msg.payload.get("device_id"))

    if not valid:
        return

    try:
        _publish_with_retry(publisher, valid)
        logger.info("Published {} message(s) to {}", len(valid), publisher.settings.mqtt_topic)
    except ConnectionError as exc:
        logger.error("Publish failed after retries: {} — caching {} messages", exc, len(valid))
        for msg in valid:
            cache.append(msg)


def run() -> None:
    settings = get_settings()
    logger.remove()
    logger.add(sys.stdout, level="DEBUG" if settings.environment == "development" else "INFO",
               format="{time:HH:mm:ss} | {level:<8} | {message}")

    logger.info("=== VineGuard Gateway starting (mode={}, env={}) ===",
                settings.lora_mode, settings.environment)

    health_server = start_health_server(settings)
    lora          = LoRaInterface(settings)
    cache         = OfflineCache(settings.offline_cache_path)
    publisher     = MqttPublisher(settings)

    def shutdown(*_: int) -> None:
        logger.info("Shutdown signal received")
        _shutdown_event.set()
        health_server.shutdown()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    lora.open()
    publisher.connect()

    logger.info("Gateway ready – polling every 5 s")
    while not _shutdown_event.is_set():
        # Drain offline cache first (backlogged messages from when broker was down)
        cached = cache.drain()
        if cached:
            logger.info("Draining {} cached messages", len(cached))
            _process_messages(cached, publisher, cache)

        # Read new messages from LoRa interface
        messages = list(lora.read_messages())
        if messages:
            _process_messages(messages, publisher, cache)

        sleep(5)

    health_server.server_close()
    logger.info("Gateway shut down cleanly")


if __name__ == "__main__":
    run()
