from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException, Query, status
from redis.asyncio import Redis

from .config import ApiSettings, get_settings


async def get_api_settings() -> ApiSettings:
    return get_settings()


async def api_key_auth(
    x_api_key: str | None = Header(default=None),
    api_key_query: str | None = Query(default=None, alias="api_key"),
    settings: ApiSettings = Depends(get_api_settings),
) -> None:
    candidate = x_api_key or api_key_query
    if candidate != settings.security.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


async def get_redis(settings: ApiSettings = Depends(get_api_settings)) -> AsyncIterator[Redis]:
    redis = Redis.from_url(settings.redis.url)
    try:
        yield redis
    finally:
        await redis.aclose()
