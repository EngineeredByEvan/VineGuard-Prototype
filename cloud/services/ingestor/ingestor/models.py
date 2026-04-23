from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table, text
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

telemetry_table = Table(
    "telemetry_readings",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("device_id", String(length=64), nullable=False),
    Column("node_id", UUID(as_uuid=True), nullable=True),
    Column("soil_moisture", Float, nullable=False),
    Column("soil_temp_c", Float, nullable=False),
    Column("ambient_temp_c", Float, nullable=False),
    Column("ambient_humidity", Float, nullable=False),
    Column("light_lux", Float, nullable=False),
    Column("battery_voltage", Float, nullable=False),
    Column("leaf_wetness_pct", Float, nullable=True),
    Column("pressure_hpa", Float, nullable=True),
    Column("schema_version", String(length=8), nullable=True),
    Column("recorded_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
)

nodes_table = Table(
    "nodes",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("block_id", UUID(as_uuid=True), nullable=True),
    Column("device_id", String(length=64), nullable=False, unique=True),
    Column("name", String, nullable=True),
    Column("tier", String(length=16), nullable=True),
    Column("last_seen_at", DateTime(timezone=True), nullable=True),
    Column("battery_voltage", Float, nullable=True),
    Column("battery_pct", Integer, nullable=True),
    Column("rssi_last", Integer, nullable=True),
    Column("status", String(length=16), nullable=True),
)
