from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from ..database import get_session
from ..dependencies import api_key_auth, get_api_settings, get_redis

router = APIRouter()


@router.get("/healthz", tags=["system"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readings", response_model=list[schemas.TelemetryOut], dependencies=[Depends(api_key_auth)])
async def list_readings(limit: int = 100, session: AsyncSession = Depends(get_session)) -> list[schemas.TelemetryOut]:
    query = select(models.telemetry_readings).order_by(models.telemetry_readings.c.recorded_at.desc()).limit(limit)
    result = await session.execute(query)
    rows = result.fetchall()
    return [schemas.TelemetryOut(**row._mapping) for row in rows]


@router.post("/readings", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(api_key_auth)])
async def create_reading(payload: schemas.TelemetryIn, session: AsyncSession = Depends(get_session)) -> Response:
    values = payload.model_dump()
    if values.get("recorded_at") is None:
        values.pop("recorded_at")
    await session.execute(models.telemetry_readings.insert().values(**values))
    await session.commit()
    return Response(status_code=status.HTTP_202_ACCEPTED)


async def telemetry_event_stream(redis: Redis) -> AsyncIterator[dict[str, str]]:
    pubsub = redis.pubsub()
    settings = await get_api_settings()
    await pubsub.subscribe(settings.redis.telemetry_channel)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                payload = message["data"]
                if isinstance(payload, bytes):
                    payload = payload.decode("utf-8")
                yield {"data": payload}
    finally:
        await pubsub.unsubscribe(settings.redis.telemetry_channel)
        await pubsub.close()


@router.get("/streams/telemetry", dependencies=[Depends(api_key_auth)])
async def stream_telemetry(redis: Redis = Depends(get_redis)) -> EventSourceResponse:
    return EventSourceResponse(telemetry_event_stream(redis))
