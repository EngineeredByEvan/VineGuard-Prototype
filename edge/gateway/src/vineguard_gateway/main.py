from __future__ import annotations

import signal
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Thread
from time import sleep

from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import GatewaySettings, get_settings
from .lora import LoRaInterface, OfflineCache
from .mqtt_client import MqttPublisher

_shutdown_event = Event()


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def start_health_server(settings: GatewaySettings) -> HTTPServer:
    server = HTTPServer(("0.0.0.0", settings.health_port), HealthHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(ConnectionError),
)
def publish_with_retry(publisher: MqttPublisher, messages):
    publisher.publish_messages(messages)


def run() -> None:
    settings = get_settings()
    logger.add(sys.stdout, level="INFO")

    health_server = start_health_server(settings)
    lora = LoRaInterface(settings.lora_serial_port, settings.lora_baud_rate)
    cache = OfflineCache(settings.offline_cache_path)
    publisher = MqttPublisher(settings)

    def shutdown(*_: int) -> None:
        _shutdown_event.set()
        health_server.shutdown()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    lora.open()
    publisher.connect()

    while not _shutdown_event.is_set():
        messages = list(lora.read_messages())
        cached = cache.drain()
        combined = cached + messages
        if combined:
            try:
                publish_with_retry(publisher, combined)
            except ConnectionError:
                for message in combined:
                    cache.append(message)
        sleep(5)

    health_server.server_close()
    logger.info("Gateway shut down cleanly")


if __name__ == "__main__":
    run()
