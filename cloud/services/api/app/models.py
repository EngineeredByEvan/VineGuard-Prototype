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

metadata_obj = MetaData()

vineyards = Table(
    "vineyards",
    metadata_obj,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("name", Text, nullable=False),
    Column("region", Text, nullable=False),
    Column("owner_name", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
)

blocks = Table(
    "blocks",
    metadata_obj,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("vineyard_id", UUID(as_uuid=True), nullable=False, index=True),
    Column("name", Text, nullable=False),
    Column("variety", Text, nullable=False),
    Column("area_ha", Float, nullable=True),
    Column("row_spacing_m", Float, nullable=True),
    Column("reference_lux_peak", Float, nullable=True),
    Column("notes", Text, nullable=True, server_default=text("''")),
    Column("created_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
)

nodes = Table(
    "nodes",
    metadata_obj,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("block_id", UUID(as_uuid=True), nullable=False, index=True),
    Column("device_id", String(length=64), nullable=False, unique=True),
    Column("name", Text, nullable=False),
    Column("tier", String(length=16), nullable=False, server_default=text("'basic'")),
    Column("lat", Float, nullable=True),
    Column("lon", Float, nullable=True),
    Column("installed_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
    Column("firmware_version", String(length=32), nullable=True),
    Column("last_seen_at", DateTime(timezone=True), nullable=True),
    Column("battery_voltage", Float, nullable=True),
    Column("battery_pct", Integer, nullable=True),
    Column("rssi_last", Integer, nullable=True),
    Column("status", String(length=16), nullable=False, server_default=text("'active'")),
)

gateways = Table(
    "gateways",
    metadata_obj,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("vineyard_id", UUID(as_uuid=True), nullable=False, index=True),
    Column("name", Text, nullable=False),
    Column("device_id", String(length=64), nullable=False, unique=True),
    Column("last_seen_at", DateTime(timezone=True), nullable=True),
    Column("firmware_version", String(length=32), nullable=True),
    Column("status", String(length=16), nullable=True),
)

users = Table(
    "users",
    metadata_obj,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("email", String(length=255), nullable=False, unique=True),
    Column("hashed_password", String(length=255), nullable=False),
    Column("role", String(length=16), nullable=False, server_default=text("'viewer'")),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("created_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
)

telemetry_readings = Table(
    "telemetry_readings",
    metadata_obj,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("device_id", String(length=64), nullable=False, index=True),
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

alerts = Table(
    "alerts",
    metadata_obj,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("node_id", UUID(as_uuid=True), nullable=True),
    Column("block_id", UUID(as_uuid=True), nullable=True),
    Column("vineyard_id", UUID(as_uuid=True), nullable=False, index=True),
    Column("rule_key", String(length=64), nullable=False),
    Column("severity", String(length=16), nullable=False),
    Column("title", String(length=128), nullable=False),
    Column("message", Text, nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("triggered_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
    Column("resolved_at", DateTime(timezone=True), nullable=True),
    Column("cooldown_until", DateTime(timezone=True), nullable=True),
)

recommendations = Table(
    "recommendations",
    metadata_obj,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("alert_id", UUID(as_uuid=True), nullable=True),
    Column("block_id", UUID(as_uuid=True), nullable=True),
    Column("vineyard_id", UUID(as_uuid=True), nullable=False, index=True),
    Column("action_text", Text, nullable=False),
    Column("priority", Integer, nullable=False),
    Column("due_by", DateTime(timezone=True), nullable=True),
    Column("is_acknowledged", Boolean, nullable=False, server_default=text("false")),
    Column("acknowledged_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
)

gdd_accumulation = Table(
    "gdd_accumulation",
    metadata_obj,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("vineyard_id", UUID(as_uuid=True), nullable=False, index=True),
    Column("date", Date, nullable=False),
    Column("gdd_daily", Float, nullable=False),
    Column("gdd_season_total", Float, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=text("now()"), nullable=False),
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
