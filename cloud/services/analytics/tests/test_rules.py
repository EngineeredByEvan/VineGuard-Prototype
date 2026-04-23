"""Tests for the VineGuard analytics rules engine.

Each test exercises the core logic of a rule module using mock async
database connections — no real database is required.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_uuid() -> str:
    return str(uuid.uuid4())


def _make_mapping(**kwargs) -> SimpleNamespace:
    """Return a SimpleNamespace that behaves like a SQLAlchemy row mapping."""
    ns = SimpleNamespace(**kwargs)
    ns.__getitem__ = lambda self, key: getattr(self, key)
    return ns


class _FakeResult:
    """Minimal stand-in for the object returned by conn.execute()."""

    def __init__(self, rows: list[dict]):
        self._rows = [SimpleNamespace(**r) for r in rows]

    def mappings(self) -> "_FakeResult":
        return self

    def all(self) -> list[SimpleNamespace]:
        return self._rows

    def first(self) -> SimpleNamespace | None:
        return self._rows[0] if self._rows else None

    def scalar(self) -> Any:
        return list(self._rows[0].__dict__.values())[0] if self._rows else None


def _row(**kwargs) -> dict:
    return kwargs


# ---------------------------------------------------------------------------
# 1. Moisture rule — critical alert when avg < 15%
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_moisture_dry_alert_created():
    """Moisture rule should create a 'critical' alert when avg_moisture < 15%."""
    node_id = _make_uuid()
    block_id = _make_uuid()
    vineyard_id = _make_uuid()

    telemetry_row = _row(
        node_id=uuid.UUID(node_id),
        device_id="dev-001",
        block_id=uuid.UUID(block_id),
        block_name="Block A",
        vineyard_id=uuid.UUID(vineyard_id),
        avg_moisture=8.5,   # below 15% → dry → critical
    )

    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_FakeResult([telemetry_row]))

    engine = MagicMock()
    engine.begin = MagicMock(return_value=_async_ctx(conn))

    created_alerts: list[dict] = []
    created_recs: list[dict] = []

    async def fake_create_alert(conn, *, node_id, block_id, vineyard_id, rule_key,
                                severity, title, message, cooldown_hours=4):
        created_alerts.append(dict(
            node_id=node_id, block_id=block_id, vineyard_id=vineyard_id,
            rule_key=rule_key, severity=severity, title=title, message=message,
        ))
        return _make_uuid()

    async def fake_create_recommendation(conn, *, alert_id, block_id, vineyard_id,
                                         action_text, priority=2, due_by=None):
        created_recs.append(dict(action_text=action_text, priority=priority))
        return _make_uuid()

    async def fake_resolve(conn, rule_key, still_triggering):
        pass  # no-op for this test

    with (
        patch("analytics.rules.moisture.create_alert", side_effect=fake_create_alert),
        patch("analytics.rules.moisture.create_recommendation", side_effect=fake_create_recommendation),
        patch("analytics.rules.moisture.resolve_alerts_for_rule", side_effect=fake_resolve),
    ):
        from analytics.rules import moisture
        await moisture.run(engine)

    assert len(created_alerts) == 1
    alert = created_alerts[0]
    assert alert["rule_key"] == "moisture_dry"
    assert alert["severity"] == "critical"
    assert "8.5%" in alert["message"]
    assert "15%" in alert["message"]

    assert len(created_recs) == 1
    assert "Block A" in created_recs[0]["action_text"]
    assert created_recs[0]["priority"] == 1


@pytest.mark.asyncio
async def test_moisture_wet_alert_created():
    """Moisture rule should create a 'warning' alert when avg_moisture > 75%."""
    node_id = _make_uuid()
    block_id = _make_uuid()
    vineyard_id = _make_uuid()

    telemetry_row = _row(
        node_id=uuid.UUID(node_id),
        device_id="dev-002",
        block_id=uuid.UUID(block_id),
        block_name="Block B",
        vineyard_id=uuid.UUID(vineyard_id),
        avg_moisture=82.0,  # above 75% → wet → warning
    )

    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_FakeResult([telemetry_row]))
    engine = MagicMock()
    engine.begin = MagicMock(return_value=_async_ctx(conn))

    created_alerts: list[dict] = []

    async def fake_create_alert(conn, *, node_id, block_id, vineyard_id, rule_key,
                                severity, title, message, cooldown_hours=4):
        created_alerts.append(dict(rule_key=rule_key, severity=severity))
        return _make_uuid()

    async def fake_noop(*args, **kwargs):
        return _make_uuid()

    async def fake_resolve(*args, **kwargs):
        pass

    with (
        patch("analytics.rules.moisture.create_alert", side_effect=fake_create_alert),
        patch("analytics.rules.moisture.create_recommendation", side_effect=fake_noop),
        patch("analytics.rules.moisture.resolve_alerts_for_rule", side_effect=fake_resolve),
    ):
        from analytics.rules import moisture
        await moisture.run(engine)

    assert len(created_alerts) == 1
    assert created_alerts[0]["rule_key"] == "moisture_wet"
    assert created_alerts[0]["severity"] == "warning"


@pytest.mark.asyncio
async def test_moisture_no_alert_in_range():
    """Moisture rule should create no alert when avg_moisture is 35% (in normal range)."""
    node_id = _make_uuid()
    block_id = _make_uuid()
    vineyard_id = _make_uuid()

    telemetry_row = _row(
        node_id=uuid.UUID(node_id),
        device_id="dev-003",
        block_id=uuid.UUID(block_id),
        block_name="Block C",
        vineyard_id=uuid.UUID(vineyard_id),
        avg_moisture=35.0,   # normal — no alert
    )

    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_FakeResult([telemetry_row]))
    engine = MagicMock()
    engine.begin = MagicMock(return_value=_async_ctx(conn))

    created_alerts: list[dict] = []

    async def fake_create_alert(conn, **kwargs):
        created_alerts.append(kwargs)
        return _make_uuid()

    async def fake_resolve(*args, **kwargs):
        pass

    with (
        patch("analytics.rules.moisture.create_alert", side_effect=fake_create_alert),
        patch("analytics.rules.moisture.create_recommendation", new_callable=AsyncMock),
        patch("analytics.rules.moisture.resolve_alerts_for_rule", side_effect=fake_resolve),
    ):
        from analytics.rules import moisture
        await moisture.run(engine)

    assert len(created_alerts) == 0


# ---------------------------------------------------------------------------
# 2. Frost — dewpoint calculation
# ---------------------------------------------------------------------------

def test_frost_dewpoint_formula():
    """Dewpoint formula T - ((100 - RH) / 5) should be computed correctly."""
    from analytics.rules.frost import _dewpoint

    # At 100% RH dewpoint equals temperature
    assert _dewpoint(10.0, 100.0) == pytest.approx(10.0)

    # Standard example: T=5°C, RH=80% → dewpoint = 5 - (20/5) = 1.0
    assert _dewpoint(5.0, 80.0) == pytest.approx(1.0)

    # T=0°C, RH=50% → dewpoint = 0 - (50/5) = -10.0
    assert _dewpoint(0.0, 50.0) == pytest.approx(-10.0)

    # T=20°C, RH=60% → dewpoint = 20 - (40/5) = 12.0
    assert _dewpoint(20.0, 60.0) == pytest.approx(12.0)


@pytest.mark.asyncio
async def test_frost_critical_alert_below_zero():
    """Frost rule should fire a 'critical' alert when temp < 0°C."""
    node_id = _make_uuid()
    block_id = _make_uuid()
    vineyard_id = _make_uuid()

    telemetry_row = _row(
        node_id=uuid.UUID(node_id),
        device_id="dev-010",
        block_id=uuid.UUID(block_id),
        block_name="Frost Block",
        vineyard_id=uuid.UUID(vineyard_id),
        ambient_temp_c=-2.5,
        ambient_humidity=85.0,
    )

    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_FakeResult([telemetry_row]))
    engine = MagicMock()
    engine.begin = MagicMock(return_value=_async_ctx(conn))

    created_alerts: list[dict] = []

    async def fake_create_alert(conn, *, node_id, block_id, vineyard_id, rule_key,
                                severity, title, message, cooldown_hours=4):
        created_alerts.append(dict(rule_key=rule_key, severity=severity, title=title))
        return _make_uuid()

    async def fake_noop(*args, **kwargs):
        return _make_uuid()

    async def fake_resolve(*args, **kwargs):
        pass

    with (
        patch("analytics.rules.frost.create_alert", side_effect=fake_create_alert),
        patch("analytics.rules.frost.create_recommendation", side_effect=fake_noop),
        patch("analytics.rules.frost.resolve_alerts_for_rule", side_effect=fake_resolve),
    ):
        from analytics.rules import frost
        await frost.run(engine)

    assert len(created_alerts) == 1
    assert created_alerts[0]["rule_key"] == "frost_critical"
    assert created_alerts[0]["severity"] == "critical"
    assert "Frost Alert" in created_alerts[0]["title"]


@pytest.mark.asyncio
async def test_frost_warning_alert_between_zero_and_three():
    """Frost rule should fire a 'warning' alert when 0°C <= temp < 3°C."""
    node_id = _make_uuid()
    block_id = _make_uuid()
    vineyard_id = _make_uuid()

    telemetry_row = _row(
        node_id=uuid.UUID(node_id),
        device_id="dev-011",
        block_id=uuid.UUID(block_id),
        block_name="Cold Block",
        vineyard_id=uuid.UUID(vineyard_id),
        ambient_temp_c=1.8,
        ambient_humidity=90.0,
    )

    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_FakeResult([telemetry_row]))
    engine = MagicMock()
    engine.begin = MagicMock(return_value=_async_ctx(conn))

    created_alerts: list[dict] = []

    async def fake_create_alert(conn, *, node_id, block_id, vineyard_id, rule_key,
                                severity, title, message, cooldown_hours=4):
        created_alerts.append(dict(rule_key=rule_key, severity=severity))
        return _make_uuid()

    async def fake_noop(*args, **kwargs):
        return _make_uuid()

    async def fake_resolve(*args, **kwargs):
        pass

    with (
        patch("analytics.rules.frost.create_alert", side_effect=fake_create_alert),
        patch("analytics.rules.frost.create_recommendation", side_effect=fake_noop),
        patch("analytics.rules.frost.resolve_alerts_for_rule", side_effect=fake_resolve),
    ):
        from analytics.rules import frost
        await frost.run(engine)

    assert len(created_alerts) == 1
    assert created_alerts[0]["rule_key"] == "frost_warning"
    assert created_alerts[0]["severity"] == "warning"


# ---------------------------------------------------------------------------
# 3. Mildew MPI — high risk condition
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mildew_high_mpi_alert():
    """Mildew rule should fire 'critical' when wet_hours >= 2, temp in range, RH >= 78%."""
    node_id = _make_uuid()
    block_id = _make_uuid()
    vineyard_id = _make_uuid()

    # wet_reading_count=5 → 5 * 0.5 = 2.5 wet hours (>= 2)
    telemetry_row = _row(
        node_id=uuid.UUID(node_id),
        device_id="dev-020",
        tier="precision_plus",
        block_id=uuid.UUID(block_id),
        block_name="Mildew Block",
        vineyard_id=uuid.UUID(vineyard_id),
        wet_reading_count=5,     # 5 × 0.5 h = 2.5 wet hours
        avg_temp=20.0,           # in [15, 27]
        avg_humidity=82.0,       # >= 78
        total_readings=12,
    )

    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_FakeResult([telemetry_row]))
    engine = MagicMock()
    engine.begin = MagicMock(return_value=_async_ctx(conn))

    created_alerts: list[dict] = []

    async def fake_create_alert(conn, *, node_id, block_id, vineyard_id, rule_key,
                                severity, title, message, cooldown_hours=6):
        created_alerts.append(dict(rule_key=rule_key, severity=severity, message=message))
        return _make_uuid()

    async def fake_noop(*args, **kwargs):
        return _make_uuid()

    async def fake_resolve(*args, **kwargs):
        pass

    with (
        patch("analytics.rules.mildew_mpi.create_alert", side_effect=fake_create_alert),
        patch("analytics.rules.mildew_mpi.create_recommendation", side_effect=fake_noop),
        patch("analytics.rules.mildew_mpi.resolve_alerts_for_rule", side_effect=fake_resolve),
    ):
        from analytics.rules import mildew_mpi
        await mildew_mpi.run(engine)

    assert len(created_alerts) == 1
    assert created_alerts[0]["rule_key"] == "mildew_high"
    assert created_alerts[0]["severity"] == "critical"
    assert "2.5h+" in created_alerts[0]["message"]


@pytest.mark.asyncio
async def test_mildew_moderate_mpi_alert():
    """Mildew rule should fire 'warning' when wet_hours >= 1, temp in range, RH >= 70%."""
    node_id = _make_uuid()
    block_id = _make_uuid()
    vineyard_id = _make_uuid()

    # wet_reading_count=2 → 2 * 0.5 = 1.0 wet hours (>= 1 but < 2)
    telemetry_row = _row(
        node_id=uuid.UUID(node_id),
        device_id="dev-021",
        tier="precision_plus",
        block_id=uuid.UUID(block_id),
        block_name="Risk Block",
        vineyard_id=uuid.UUID(vineyard_id),
        wet_reading_count=2,     # 1 wet hour
        avg_temp=22.0,
        avg_humidity=73.0,       # >= 70 but < 78
        total_readings=12,
    )

    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_FakeResult([telemetry_row]))
    engine = MagicMock()
    engine.begin = MagicMock(return_value=_async_ctx(conn))

    created_alerts: list[dict] = []

    async def fake_create_alert(conn, *, node_id, block_id, vineyard_id, rule_key,
                                severity, title, message, cooldown_hours=6):
        created_alerts.append(dict(rule_key=rule_key, severity=severity))
        return _make_uuid()

    async def fake_noop(*args, **kwargs):
        return _make_uuid()

    async def fake_resolve(*args, **kwargs):
        pass

    with (
        patch("analytics.rules.mildew_mpi.create_alert", side_effect=fake_create_alert),
        patch("analytics.rules.mildew_mpi.create_recommendation", side_effect=fake_noop),
        patch("analytics.rules.mildew_mpi.resolve_alerts_for_rule", side_effect=fake_resolve),
    ):
        from analytics.rules import mildew_mpi
        await mildew_mpi.run(engine)

    assert len(created_alerts) == 1
    assert created_alerts[0]["rule_key"] == "mildew_moderate"
    assert created_alerts[0]["severity"] == "warning"


@pytest.mark.asyncio
async def test_mildew_no_alert_for_basic_tier():
    """Mildew rule should not create any alert for a basic-tier node (excluded by query filter)."""
    # The tier filter is in the SQL WHERE clause, so the query returns nothing for basic nodes.
    # Simulate an empty result set.
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_FakeResult([]))
    engine = MagicMock()
    engine.begin = MagicMock(return_value=_async_ctx(conn))

    created_alerts: list[dict] = []

    async def fake_create_alert(conn, **kwargs):
        created_alerts.append(kwargs)
        return _make_uuid()

    async def fake_resolve(*args, **kwargs):
        pass

    with (
        patch("analytics.rules.mildew_mpi.create_alert", side_effect=fake_create_alert),
        patch("analytics.rules.mildew_mpi.create_recommendation", new_callable=AsyncMock),
        patch("analytics.rules.mildew_mpi.resolve_alerts_for_rule", side_effect=fake_resolve),
    ):
        from analytics.rules import mildew_mpi
        await mildew_mpi.run(engine)

    assert len(created_alerts) == 0


# ---------------------------------------------------------------------------
# 4. GDD calculation
# ---------------------------------------------------------------------------

def test_gdd_calculation_above_base():
    """GDD = max(0, (max + min) / 2 - 10) for typical warm day."""
    # 28°C max, 14°C min → mean = 21, GDD = 21 - 10 = 11
    daily_max = 28.0
    daily_min = 14.0
    base_temp = 10.0

    gdd = max(0.0, (daily_max + daily_min) / 2.0 - base_temp)
    assert gdd == pytest.approx(11.0)


def test_gdd_calculation_cold_day_zero():
    """GDD should be 0 when the mean temperature is at or below base (10°C)."""
    # 8°C max, 4°C min → mean = 6, GDD = max(0, 6 - 10) = 0
    daily_max = 8.0
    daily_min = 4.0
    base_temp = 10.0

    gdd = max(0.0, (daily_max + daily_min) / 2.0 - base_temp)
    assert gdd == pytest.approx(0.0)


def test_gdd_calculation_exact_base():
    """GDD should be 0 when mean temp exactly equals base temp."""
    daily_max = 12.0
    daily_min = 8.0   # mean = 10.0 = base → GDD = 0
    base_temp = 10.0

    gdd = max(0.0, (daily_max + daily_min) / 2.0 - base_temp)
    assert gdd == pytest.approx(0.0)


def test_gdd_calculation_hot_day():
    """GDD accumulates correctly for a hot day."""
    # 35°C max, 20°C min → mean = 27.5, GDD = 27.5 - 10 = 17.5
    daily_max = 35.0
    daily_min = 20.0
    base_temp = 10.0

    gdd = max(0.0, (daily_max + daily_min) / 2.0 - base_temp)
    assert gdd == pytest.approx(17.5)


@pytest.mark.asyncio
async def test_gdd_upsert_called():
    """GDD rule should upsert a gdd_accumulation row for each vineyard."""
    vineyard_id = _make_uuid()

    temp_row = _row(
        vineyard_id=uuid.UUID(vineyard_id),
        vineyard_name="Test Vineyard",
        daily_max=28.0,
        daily_min=14.0,
    )

    # The rule calls conn.execute three times per vineyard:
    # 1. main temp query
    # 2. season total subquery (scalar)
    # 3. upsert
    # Then once per milestone that fires (0 in this test since season_total=11).
    scalar_result = MagicMock()
    scalar_result.scalar = MagicMock(return_value=0.0)

    execute_results = [
        _FakeResult([temp_row]),  # main query
        scalar_result,            # season total
        MagicMock(),              # upsert
    ]
    execute_iter = iter(execute_results)

    conn = AsyncMock()
    conn.execute = AsyncMock(side_effect=lambda *a, **kw: next(execute_iter))
    engine = MagicMock()
    engine.begin = MagicMock(return_value=_async_ctx(conn))

    async def fake_create_alert(*args, **kwargs):
        return _make_uuid()

    async def fake_create_rec(*args, **kwargs):
        return _make_uuid()

    with (
        patch("analytics.rules.gdd.create_alert", side_effect=fake_create_alert),
        patch("analytics.rules.gdd.create_recommendation", side_effect=fake_create_rec),
    ):
        from analytics.rules import gdd
        await gdd.run(engine)

    # Verify execute was called at least 3 times (main query + subquery + upsert)
    assert conn.execute.call_count >= 3


# ---------------------------------------------------------------------------
# 5. Alert manager — cooldown prevents duplicate creation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_alert_skips_during_cooldown():
    """create_alert should not insert a new row if an active alert is within cooldown."""
    from analytics.alert_manager import create_alert

    existing_id = _make_uuid()
    future_cooldown = datetime(2030, 1, 1, tzinfo=timezone.utc)

    existing_alert = _row(
        id=uuid.UUID(existing_id),
        rule_key="moisture_dry",
        is_active=True,
        cooldown_until=future_cooldown,
    )

    conn = AsyncMock()
    # get_active_alert calls conn.execute → returns the existing alert
    conn.execute = AsyncMock(return_value=_FakeResult([existing_alert]))

    result_id = await create_alert(
        conn,
        node_id=_make_uuid(),
        block_id=_make_uuid(),
        vineyard_id=_make_uuid(),
        rule_key="moisture_dry",
        severity="critical",
        title="Low Soil Moisture — Block X",
        message="soil moisture 8.0% over 3h",
        cooldown_hours=4,
    )

    # Should return the existing alert id, not insert a new row
    assert result_id == existing_id
    # execute was called exactly once (for get_active_alert), no insert
    assert conn.execute.call_count == 1


@pytest.mark.asyncio
async def test_create_alert_inserts_when_no_active():
    """create_alert should insert a new row when no active alert exists."""
    from analytics.alert_manager import create_alert

    new_id = _make_uuid()

    # First call (get_active_alert) returns nothing; second call (insert) returns new id
    insert_result = _FakeResult([{"id": uuid.UUID(new_id)}])
    # Provide a plain first() that returns a tuple-like object
    insert_result.first = lambda: (uuid.UUID(new_id),)

    conn = AsyncMock()
    conn.execute = AsyncMock(side_effect=[
        _FakeResult([]),    # get_active_alert returns None
        insert_result,      # insert returning id
    ])

    result_id = await create_alert(
        conn,
        node_id=_make_uuid(),
        block_id=_make_uuid(),
        vineyard_id=_make_uuid(),
        rule_key="moisture_dry",
        severity="critical",
        title="Low Soil Moisture — Block X",
        message="soil moisture 8.0% over 3h",
        cooldown_hours=4,
    )

    assert result_id == new_id
    assert conn.execute.call_count == 2  # get_active_alert + insert


# ---------------------------------------------------------------------------
# Async context manager helper
# ---------------------------------------------------------------------------

class _async_ctx:
    """Simple async context manager that yields a pre-built connection mock."""

    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass
