from __future__ import annotations

"""Simple HTTP health endpoint for observability."""

from aiohttp import web

from .config import Config
from .gateway import Gateway


class HealthServer:
    def __init__(self, config: Config, gateway: Gateway) -> None:
        self._config = config
        self._gateway = gateway
        self._runner: web.AppRunner | None = None

    async def start(self) -> None:
        app = web.Application()
        app.add_routes([web.get("/healthz", self._handle_health)])
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, host="0.0.0.0", port=self._config.health_port)
        await site.start()

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

    async def _handle_health(self, request: web.Request) -> web.Response:
        status = self._gateway.build_health_status()
        return web.json_response(status)


__all__ = ["HealthServer"]
