from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

vineyards = Table(
    "vineyards",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("name", Text, nullable=False),
    Column("region", Text, nullable=True),
    Column("owner_name", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
)

blocks = Table(
    "blocks",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("vineyard_id", UUID(as_uuid=True), nullable=False),
    Column("name", Text, nullable=False),
    Column("variety", Text, nullable=True),
    Column("area_ha", Float, nullable=True),
    Column("row_spacing_m", Float, nullable=True),
    Column("reference_lux_peak", Float, nullable=True),
    Column("notes", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
)

nodes = Table(
    "nodes",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("block_id", UUID(as_uuid=True), nullable=False),
    Column("device_id", String(64), nullable=False),
    Column("name", Text, nullable=True),
    Column("tier", String(16), nullable=False),  # 'basic' | 'precision_plus'
    Column("lat", Float, nullable=True),
    Column("lon", Float, nullable=True),
    Column("installed_at", DateTime(timezone=True), nullable=True),
    Column("firmware_version", String(32), nullable=True),
    Column("last_seen_at", DateTime(timezone=True), nullable=True),
    Column("battery_voltage", Float, nullable=True),
    Column("battery_pct", Integer, nullable=True),
    Column("rssi_last", Integer, nullable=True),
    Column("status", String(16), nullable=True),
)

telemetry_readings = Table(
    "telemetry_readings",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("device_id", String(64), nullable=False),
    Column("node_id", UUID(as_uuid=True), nullable=True),
    Column("soil_moisture", Float, nullable=True),
    Column("soil_temp_c", Float, nullable=True),
    Column("ambient_temp_c", Float, nullable=True),
    Column("ambient_humidity", Float, nullable=True),
    Column("light_lux", Float, nullable=True),
    Column("battery_voltage", Float, nullable=True),
    Column("leaf_wetness_pct", Float, nullable=True),
    Column("pressure_hpa", Float, nullable=True),
    Column("schema_version", String(8), nullable=True),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
)

alerts = Table(
    "alerts",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("node_id", UUID(as_uuid=True), nullable=True),
    Column("block_id", UUID(as_uuid=True), nullable=True),
    Column("vineyard_id", UUID(as_uuid=True), nullable=False),
    Column("rule_key", String(64), nullable=False),
    Column("severity", String(16), nullable=False),  # 'info' | 'warning' | 'critical'
    Column("title", String(128), nullable=False),
    Column("message", Text, nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("triggered_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
    Column("resolved_at", DateTime(timezone=True), nullable=True),
    Column("cooldown_until", DateTime(timezone=True), nullable=True),
)

recommendations = Table(
    "recommendations",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("alert_id", UUID(as_uuid=True), nullable=True),
    Column("block_id", UUID(as_uuid=True), nullable=True),
    Column("vineyard_id", UUID(as_uuid=True), nullable=False),
    Column("action_text", Text, nullable=False),
    Column("priority", Integer, nullable=False, server_default=text("2")),  # 1=high 2=med 3=low
    Column("due_by", DateTime(timezone=True), nullable=True),
    Column("is_acknowledged", Boolean, nullable=False, server_default=text("false")),
    Column("acknowledged_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
)

gdd_accumulation = Table(
    "gdd_accumulation",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("vineyard_id", UUID(as_uuid=True), nullable=False),
    Column("date", Date, nullable=False),
    Column("gdd_daily", Float, nullable=False),
    Column("gdd_season_total", Float, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
)

# Kept for backwards compatibility — no longer the primary signal store.
analytics_signals = Table(
    "analytics_signals",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("device_id", String(64), nullable=False),
    Column("signal_type", String(32), nullable=False),
    Column("severity", String(16), nullable=False),
    Column("description", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
)
