from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import paho.mqtt.publish as publish
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.deps import get_current_org, get_current_user
from ..auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from ..config import get_settings
from ..db import session_dependency
from ..models import Insight, Node, NodeStatus, TelemetryRaw, User
from ..schemas.auth import LoginRequest, RefreshRequest, TokenPair
from ..schemas.telemetry import DownlinkCommand

logger = logging.getLogger(__name__)

settings = get_settings()
app = FastAPI(title="VineGuard API", version="0.1.0")

if settings.cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.cors_allow_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.post("/auth/login", response_model=TokenPair)
async def login(request: LoginRequest, session: AsyncSession = Depends(session_dependency())) -> TokenPair:
    result = await session.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token, access_exp = create_access_token(user.email, user.org_id, user.role.value)
    refresh_token, _ = create_refresh_token(user.email, user.org_id, user.role.value)

    return TokenPair(access_token=access_token, refresh_token=refresh_token, expires_at=access_exp)


@app.post("/auth/refresh", response_model=TokenPair)
async def refresh(request: RefreshRequest, session: AsyncSession = Depends(session_dependency())) -> TokenPair:
    try:
        payload = decode_token(request.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    result = await session.execute(select(User).where(User.email == payload.get("sub")))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token, access_exp = create_access_token(user.email, user.org_id, user.role.value)
    refresh_token, _ = create_refresh_token(user.email, user.org_id, user.role.value)

    return TokenPair(access_token=access_token, refresh_token=refresh_token, expires_at=access_exp)


@app.get("/auth/me")
async def get_profile(user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "email": user.email,
        "orgId": user.org_id,
        "role": user.role.value,
        "createdAt": user.created_at,
    }


@app.get("/api/nodes/status")
async def node_status(
    org_id: str = Depends(get_current_org), session: AsyncSession = Depends(session_dependency())
) -> list[dict[str, Any]]:
    result = await session.execute(select(NodeStatus).where(NodeStatus.org_id == org_id))
    statuses = []
    for row in result.scalars():
        statuses.append(
            {
                "orgId": row.org_id,
                "siteId": row.site_id,
                "nodeId": row.node_id,
                "lastSeen": row.last_seen,
                "batteryV": row.battery_v,
                "fwVersion": row.fw_version,
                "health": row.health,
            }
        )
    return statuses


@app.get("/api/telemetry/latest")
async def latest_telemetry(
    org_id: str = Depends(get_current_org),
    site_id: str | None = None,
    session: AsyncSession = Depends(session_dependency()),
) -> list[dict[str, Any]]:
    base_filters = [TelemetryRaw.org_id == org_id]
    if site_id:
        base_filters.append(TelemetryRaw.site_id == site_id)

    subquery = (
        select(TelemetryRaw.node_id, func.max(TelemetryRaw.ts).label("max_ts"))
        .where(and_(*base_filters))
        .group_by(TelemetryRaw.node_id)
        .subquery()
    )

    stmt = (
        select(TelemetryRaw)
        .join(subquery, and_(TelemetryRaw.node_id == subquery.c.node_id, TelemetryRaw.ts == subquery.c.max_ts))
        .order_by(TelemetryRaw.node_id)
    )
    result = await session.execute(stmt)
    payloads = []
    for row in result.scalars():
        payloads.append(
            {
                "ts": row.ts,
                "orgId": row.org_id,
                "siteId": row.site_id,
                "nodeId": row.node_id,
                "sensors": {
                    "soilMoisture": row.soil_moisture,
                    "soilTempC": row.soil_temp_c,
                    "airTempC": row.air_temp_c,
                    "humidity": row.humidity,
                    "lightLux": row.light_lux,
                    "vbat": row.vbat,
                },
                "rssi": row.rssi,
                "fwVersion": row.fw_version,
            }
        )
    return payloads


@app.get("/api/telemetry/history")
async def telemetry_history(
    node_id: str,
    hours: int = 24,
    org_id: str = Depends(get_current_org),
    session: AsyncSession = Depends(session_dependency()),
) -> list[dict[str, Any]]:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    stmt = (
        select(TelemetryRaw)
        .where(
            TelemetryRaw.org_id == org_id,
            TelemetryRaw.node_id == node_id,
            TelemetryRaw.ts >= cutoff,
        )
        .order_by(TelemetryRaw.ts)
    )
    result = await session.execute(stmt)
    return [
        {
            "ts": row.ts,
            "soilMoisture": row.soil_moisture,
            "soilTempC": row.soil_temp_c,
            "airTempC": row.air_temp_c,
            "humidity": row.humidity,
            "lightLux": row.light_lux,
            "vbat": row.vbat,
        }
        for row in result.scalars()
    ]


@app.get("/api/insights")
async def list_insights(
    org_id: str = Depends(get_current_org),
    site_id: str | None = None,
    node_id: str | None = None,
    session: AsyncSession = Depends(session_dependency()),
    limit: int = 50,
) -> list[dict[str, Any]]:
    stmt = select(Insight).where(Insight.org_id == org_id)
    if site_id:
        stmt = stmt.where(Insight.site_id == site_id)
    if node_id:
        stmt = stmt.where(Insight.node_id == node_id)
    stmt = stmt.order_by(Insight.ts.desc()).limit(limit)
    result = await session.execute(stmt)
    return [
        {
            "ts": row.ts,
            "type": row.type,
            "payload": row.payload,
            "nodeId": row.node_id,
            "siteId": row.site_id,
        }
        for row in result.scalars()
    ]


@app.post("/api/nodes/{node_id}/commands")
async def send_command(
    node_id: str,
    command: DownlinkCommand,
    org_id: str = Depends(get_current_org),
    session: AsyncSession = Depends(session_dependency()),
) -> dict[str, Any]:
    result = await session.execute(select(Node).where(Node.node_id == node_id, Node.org_id == org_id))
    node = result.scalar_one_or_none()
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")

    topic = f"{settings.cmd_topic_prefix}/{org_id}/{node.site_id}/{node_id}/cmd"

    payload = json.dumps(command.model_dump(by_alias=True, exclude_none=True))
    try:
        publish.single(
            topic,
            payload=payload,
            hostname=settings.mqtt_broker_host,
            port=settings.mqtt_broker_port,
            auth={"username": settings.mqtt_username, "password": settings.mqtt_password}
            if settings.mqtt_username
            else None,
        )
    except Exception as exc:
        logger.exception("Failed to publish command")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="MQTT publish failed") from exc

    return {"topic": topic, "status": "published"}


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
