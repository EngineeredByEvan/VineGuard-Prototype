from __future__ import annotations

import uuid
from datetime import datetime

from enum import Enum

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, PrimaryKeyConstraint, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"

    org_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    sites: Mapped[list[Site]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    users: Mapped[list[User]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class Site(Base):
    __tablename__ = "sites"

    site_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="sites")
    nodes: Mapped[list["Node"]] = relationship(back_populates="site", cascade="all, delete-orphan")


class Node(Base):
    __tablename__ = "nodes"
    __table_args__ = (
        UniqueConstraint("org_id", "site_id", "node_id", name="uq_node_org_site"),
    )

    node_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Field Node")
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False)
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.site_id", ondelete="CASCADE"), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))

    site: Mapped[Site] = relationship("Site", back_populates="nodes", primaryjoin="Node.site_id==Site.site_id")


class UserRole(str, Enum):  # type: ignore[misc]
    ADMIN = "admin"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.org_id", ondelete="CASCADE"), nullable=False)
    role: Mapped[UserRole] = mapped_column(default=UserRole.VIEWER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="users")


class TelemetryRaw(Base):
    __tablename__ = "telemetry_raw"
    __table_args__ = (
        PrimaryKeyConstraint("node_id", "ts", name="pk_telemetry_raw"),
        Index("ix_telemetry_org_site_ts", "org_id", "site_id", "ts"),
    )

    org_id: Mapped[str] = mapped_column(String(64), nullable=False)
    site_id: Mapped[str] = mapped_column(String(64), nullable=False)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    soil_moisture: Mapped[float | None] = mapped_column()
    soil_temp_c: Mapped[float | None] = mapped_column()
    air_temp_c: Mapped[float | None] = mapped_column()
    humidity: Mapped[float | None] = mapped_column()
    light_lux: Mapped[float | None] = mapped_column()
    vbat: Mapped[float | None] = mapped_column()
    rssi: Mapped[int | None] = mapped_column(Integer)
    fw_version: Mapped[str | None] = mapped_column(String(32))


class NodeStatus(Base):
    __tablename__ = "node_status"
    __table_args__ = (
        PrimaryKeyConstraint("node_id", name="pk_node_status"),
        UniqueConstraint("org_id", "site_id", "node_id", name="uq_status_node"),
    )

    org_id: Mapped[str] = mapped_column(String(64), nullable=False)
    site_id: Mapped[str] = mapped_column(String(64), nullable=False)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    battery_v: Mapped[float | None] = mapped_column()
    fw_version: Mapped[str | None] = mapped_column(String(32))
    health: Mapped[str | None] = mapped_column(String(32))


class InsightType(str, Enum):  # type: ignore[misc]
    IRRIGATION = "irrigation_advice"
    DISEASE = "disease_risk"
    BATTERY = "battery_alert"
    SENSOR_FAULT = "sensor_fault"
    ANOMALY = "anomaly"


class Insight(Base):
    __tablename__ = "insights"
    __table_args__ = (
        Index("ix_insights_org_site_ts", "org_id", "site_id", "ts"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    org_id: Mapped[str] = mapped_column(String(64), nullable=False)
    site_id: Mapped[str] = mapped_column(String(64), nullable=False)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    type: Mapped[InsightType] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


metadata = Base.metadata
