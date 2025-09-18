from __future__ import annotations

"""Entry point for the VineGuard edge gateway."""

import asyncio
import signal
from contextlib import suppress

from .config import Config
from .gateway import Gateway
from .health import HealthServer
from .logging_config import configure_logging
from .mqtt_client import CloudMqttClient
from .queue_store import PersistentQueue


def _create_gateway(config: Config, queue: PersistentQueue, loop: asyncio.AbstractEventLoop) -> Gateway:
    gateway_ref: dict[str, Gateway] = {}

    def on_command(topic: str, payload: bytes) -> None:
        gateway = gateway_ref.get('gateway')
        if gateway is not None:
            gateway.handle_command(topic, payload)

    mqtt_client = CloudMqttClient(config, on_command)
    gateway = Gateway(config=config, queue=queue, mqtt_client=mqtt_client, loop=loop)
    gateway_ref['gateway'] = gateway
    return gateway


async def _run() -> None:
    config = Config.from_env()
    configure_logging(config.log_level)

    queue = PersistentQueue(config.queue_db_path)
    loop = asyncio.get_running_loop()
    gateway = _create_gateway(config, queue, loop)
    health = HealthServer(config, gateway)

    stop_event = asyncio.Event()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    gateway.mqtt.start()
    await gateway.start_sources()
    await health.start()

    try:
        await stop_event.wait()
    finally:
        await gateway.stop_sources()
        await health.stop()
        gateway.mqtt.stop()
        queue.close()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
