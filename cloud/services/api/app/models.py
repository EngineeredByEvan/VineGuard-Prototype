from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, MetaData, String, Table, text
from sqlalchemy.dialects.postgresql import UUID

metadata_obj = MetaData()

telemetry_readings = Table(
    "telemetry_readings",
    metadata_obj,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("device_id", String(length=64), nullable=False, index=True),
    Column("soil_moisture", Float, nullable=False),
    Column("soil_temp_c", Float, nullable=False),
    Column("ambient_temp_c", Float, nullable=False),
    Column("ambient_humidity", Float, nullable=False),
    Column("light_lux", Float, nullable=False),
    Column("battery_voltage", Float, nullable=False),
    Column("recorded_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
)

analytics_signals = Table(
    "analytics_signals",
    metadata_obj,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("device_id", String(length=64), nullable=False, index=True),
    Column("signal_type", String(length=32), nullable=False),
    Column("severity", String(length=16), nullable=False),
    Column("description", String(length=255), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
)
