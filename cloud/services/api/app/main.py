from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from .api.routes import router
from .config import ApiSettings, get_settings
from .logging import configure_logging

app = FastAPI(title="VineGuard Cloud API", version="0.1.0")


@app.on_event("startup")
async def on_startup() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.settings = settings
    app.state.redis = Redis.from_url(settings.redis.url)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    redis: Redis | None = getattr(app.state, "redis", None)
    if redis is not None:
        await redis.aclose()


app.include_router(router)


def run() -> None:
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False, factory=False)


if __name__ == "__main__":
    run()
