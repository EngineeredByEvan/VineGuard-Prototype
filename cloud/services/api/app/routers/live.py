import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from redis import asyncio as aioredis
from sse_starlette.sse import EventSourceResponse

from app.core.config import get_settings
from app.core.deps import get_current_user

settings = get_settings()
router = APIRouter(prefix="/live", tags=["live"])


async def stream_events(org_id: str) -> AsyncGenerator[dict, None]:
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"org:{org_id}:live")
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
            if message:
                data = json.loads(message["data"])
                yield {"event": data.get("event", "telemetry"), "data": json.dumps(data)}
            await asyncio.sleep(0.01)
    finally:
        await redis.close()


@router.get("/{org_id}")
async def live_feed(org_id: str, current_user=Depends(get_current_user)):
    if str(current_user["org_id"]) != org_id:
        raise HTTPException(status_code=403, detail="Org mismatch")

    generator = stream_events(org_id)
    return EventSourceResponse(generator)
