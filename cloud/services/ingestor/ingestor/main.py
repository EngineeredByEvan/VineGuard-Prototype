from __future__ import annotations

import asyncio
import json
import ssl
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from asyncio_mqtt import Client
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .config import IngestorSettings, get_settings
from .models import nodes_table, telemetry_table
from .schemas import parse_payload

logger = structlog.get_logger()

DEAD_LETTER_PATH = Path("/tmp/vineguard-dead-letter.jsonl")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def serialise_message(message: dict[str, Any]) -> str:
    return json.dumps(message, separators=(",", ":"), default=str)


def build_tls_context(settings: IngestorSettings) -> ssl.SSLContext:
    context = ssl.create_default_context(cafile=settings.mqtt.tls_ca_path)
    if settings.mqtt.client_cert_path and settings.mqtt.client_key_path:
        context.load_cert_chain(settings.mqtt.client_cert_path, settings.mqtt.client_key_path)
    context.check_hostname = False
    return context


def write_dead_letter(raw: str, error: str) -> None:
    """Append a rejected payload to the dead-letter file as a JSONL record."""
    record = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "error": error,
        "raw": raw,
    }
    try:
        with DEAD_LETTER_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, separators=(",", ":")) + "\n")
    except OSError as exc:
        logger.error("dead_letter_write_failed", path=str(DEAD_LETTER_PATH), error=str(exc))


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def get_node_id(conn, device_id: str) -> str | None:
    """Return the UUID string for a device_id, or None if not registered."""
    result = await conn.execute(
        select(nodes_table.c.id).where(nodes_table.c.device_id == device_id)
    )
    row = result.first()
    return str(row[0]) if row else None


async def update_node_health(conn, normalised: dict[str, Any]) -> None:
    """Update last_seen_at, battery fields, rssi, and status on the nodes row."""
    await conn.execute(
        update(nodes_table)
        .where(nodes_table.c.device_id == normalised["device_id"])
        .values(
            last_seen_at=datetime.now(tz=timezone.utc),
            battery_voltage=normalised.get("battery_voltage"),
            battery_pct=normalised.get("battery_pct"),
            rssi_last=normalised.get("rssi"),
            status="active",
        )
    )


# ---------------------------------------------------------------------------
# Core message handler
# ---------------------------------------------------------------------------

async def handle_message(
    raw_payload: str,
    redis: Redis,
    engine: AsyncEngine,
    settings: IngestorSettings,
) -> None:
    # 1. Parse JSON
    try:
        raw = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        logger.warning("invalid_json", error=str(exc))
        write_dead_letter(raw_payload, f"JSONDecodeError: {exc}")
        return

    # 2. Validate and normalise with Pydantic
    try:
        normalised = parse_payload(raw)
    except ValidationError as exc:
        logger.warning("payload_validation_failed", error=exc.json())
        write_dead_letter(raw_payload, str(exc))
        return

    _TELEMETRY_COLS = {
        "device_id", "node_id", "soil_moisture", "soil_temp_c", "ambient_temp_c",
        "ambient_humidity", "light_lux", "battery_voltage", "leaf_wetness_pct",
        "pressure_hpa", "schema_version", "recorded_at",
    }

    # 3. Persist to DB and update node health
    async with engine.begin() as conn:
        node_id = await get_node_id(conn, normalised["device_id"])

        insert_values = {k: v for k, v in normalised.items() if k in _TELEMETRY_COLS}
        insert_values["node_id"] = node_id
        result = await conn.execute(
            insert(telemetry_table).values(**insert_values).returning(telemetry_table)
        )
        row = result.mappings().one()

        await update_node_health(conn, normalised)

    # 4. Publish to Redis
    published: dict[str, Any] = {
        "id": str(row["id"]),
        "device_id": row["device_id"],
        "node_id": node_id,
        "soil_moisture": row["soil_moisture"],
        "soil_temp_c": row["soil_temp_c"],
        "ambient_temp_c": row["ambient_temp_c"],
        "ambient_humidity": row["ambient_humidity"],
        "light_lux": row["light_lux"],
        "battery_voltage": row["battery_voltage"],
        "battery_pct": row["battery_pct"],
        "leaf_wetness_pct": row["leaf_wetness_pct"],
        "pressure_hpa": row["pressure_hpa"],
        "schema_version": row["schema_version"],
        "recorded_at": row["recorded_at"].isoformat(),
    }
    await redis.publish(settings.redis.telemetry_channel, serialise_message(published))
    logger.info("ingested", device=published["device_id"], node_id=node_id)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def run_async() -> None:
    settings = get_settings()
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )
    redis = Redis.from_url(settings.redis.url)
    engine = create_async_engine(settings.database.dsn)

    # Build TLS context only when a CA path is configured
    if settings.mqtt.tls_ca_path:
        tls_context: ssl.SSLContext | None = build_tls_context(settings)
    else:
        tls_context = None

    async with Client(
        settings.mqtt.host,
        port=settings.mqtt.port,
        username=settings.mqtt.username or None,
        password=settings.mqtt.password or None,
        tls_context=tls_context,
    ) as client:
        async with client.filtered_messages(settings.mqtt.topic) as messages:
            await client.subscribe(settings.mqtt.topic)
            async for message in messages:
                raw_payload = message.payload.decode()
                try:
                    await handle_message(raw_payload, redis, engine, settings)
                except Exception as exc:  # noqa: BLE001
                    logger.error("failed_to_process", error=str(exc))


def run() -> None:
    asyncio.run(run_async())
