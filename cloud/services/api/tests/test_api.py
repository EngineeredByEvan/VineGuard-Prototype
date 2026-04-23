"""
VineGuard API tests.

Uses FastAPI TestClient with dependency overrides so no real DB or Redis is
needed.  The session dependency is replaced by a lightweight async mock that
records INSERT calls and returns pre-baked rows for SELECT queries.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Test settings — set env vars BEFORE the app is imported so pydantic-settings
# can construct ApiSettings without a real .env file.
# ---------------------------------------------------------------------------
import os

os.environ.setdefault("API_SECURITY__API_KEY", "test-api-key-1234567890abcdef")
os.environ.setdefault("API_SECURITY__JWT_SECRET", "test-jwt-secret-that-is-long-enough-for-hs256")
os.environ.setdefault("API_SECURITY__JWT_ALGORITHM", "HS256")
os.environ.setdefault("API_SECURITY__JWT_TTL_SECONDS", "3600")
os.environ.setdefault("API_DATABASE__DSN", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("API_REDIS__URL", "redis://localhost:6379/0")

from app.main import app  # noqa: E402
from app import models, schemas  # noqa: E402
from app.auth import create_access_token, hash_password  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.database import get_session  # noqa: E402
from app.dependencies import get_api_settings  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SETTINGS = get_settings()
API_KEY = SETTINGS.security.api_key
AUTH_HEADERS = {"X-API-Key": API_KEY}

_USER_ID = uuid.uuid4()
_VINEYARD_ID = uuid.uuid4()
_BLOCK_ID = uuid.uuid4()
_NODE_ID = uuid.uuid4()
_ALERT_ID = uuid.uuid4()
_REC_ID = uuid.uuid4()

_NOW = datetime.now(tz=timezone.utc)

_FAKE_USER = {
    "id": _USER_ID,
    "email": "test@vineguard.io",
    "hashed_password": hash_password("secret123"),
    "role": "operator",
    "is_active": True,
    "created_at": _NOW,
}

_FAKE_VINEYARD = {
    "id": _VINEYARD_ID,
    "name": "Test Vineyard",
    "region": "Napa",
    "owner_name": "Alice",
    "created_at": _NOW,
}

_FAKE_BLOCK = {
    "id": _BLOCK_ID,
    "vineyard_id": _VINEYARD_ID,
    "name": "Block A",
    "variety": "Cabernet Sauvignon",
    "area_ha": 2.5,
    "row_spacing_m": 1.8,
    "reference_lux_peak": 80000.0,
    "notes": "",
    "created_at": _NOW,
}

_FAKE_NODE = {
    "id": _NODE_ID,
    "block_id": _BLOCK_ID,
    "device_id": "dev-abc-001",
    "name": "Node 1",
    "tier": "basic",
    "lat": 38.5,
    "lon": -122.4,
    "installed_at": _NOW,
    "firmware_version": "1.0.0",
    "last_seen_at": _NOW,
    "battery_voltage": 3.8,
    "battery_pct": 85,
    "rssi_last": -65,
    "status": "active",
}

_FAKE_ALERT = {
    "id": _ALERT_ID,
    "node_id": _NODE_ID,
    "block_id": _BLOCK_ID,
    "vineyard_id": _VINEYARD_ID,
    "rule_key": "soil_moisture_low",
    "severity": "warning",
    "title": "Low soil moisture",
    "message": "Soil moisture below threshold",
    "is_active": True,
    "triggered_at": _NOW,
    "resolved_at": None,
    "cooldown_until": None,
}

_FAKE_REC = {
    "id": _REC_ID,
    "alert_id": _ALERT_ID,
    "block_id": _BLOCK_ID,
    "vineyard_id": _VINEYARD_ID,
    "action_text": "Irrigate block A",
    "priority": 1,
    "due_by": None,
    "is_acknowledged": False,
    "acknowledged_at": None,
    "created_at": _NOW,
}


def _make_row(data: dict) -> MagicMock:
    """Build a mock row whose ._mapping behaves like the given dict."""
    row = MagicMock()
    row._mapping = data
    return row


def _make_result(rows: list[dict] | None = None, scalar: Any = None) -> MagicMock:
    """Build a mock SQLAlchemy result object."""
    result = MagicMock()
    if rows is not None:
        mock_rows = [_make_row(r) for r in rows]
        result.fetchall.return_value = mock_rows
        result.fetchone.return_value = mock_rows[0] if mock_rows else None
    else:
        result.fetchall.return_value = []
        result.fetchone.return_value = None
    if scalar is not None:
        result.scalar.return_value = scalar
    else:
        result.scalar.return_value = 0
    return result


# ---------------------------------------------------------------------------
# Session mock factory
# ---------------------------------------------------------------------------

class MockSession:
    """Lightweight async session mock.

    Callers configure ``_responses`` as a list of result objects that are
    returned in order for each ``execute`` call.
    """

    def __init__(self, responses: list[MagicMock] | None = None) -> None:
        self._responses = list(responses or [])
        self._idx = 0
        self.committed = False

    async def execute(self, *args: Any, **kwargs: Any) -> MagicMock:
        if self._idx < len(self._responses):
            result = self._responses[self._idx]
        else:
            result = _make_result()
        self._idx += 1
        return result

    async def commit(self) -> None:
        self.committed = True

    async def __aenter__(self) -> "MockSession":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


def _session_override(responses: list[MagicMock]):
    """Return an async generator dependency that yields a MockSession."""

    async def _dep() -> AsyncIterator[MockSession]:
        yield MockSession(responses)

    return _dep


# ---------------------------------------------------------------------------
# JWT helper
# ---------------------------------------------------------------------------

def _make_token(user_id: uuid.UUID | None = None) -> str:
    uid = user_id or _USER_ID
    return create_access_token(
        data={"sub": str(uid)},
        secret=SETTINGS.security.jwt_secret,
        algorithm=SETTINGS.security.jwt_algorithm,
        ttl_seconds=SETTINGS.security.jwt_ttl_seconds,
    )


def _jwt_headers(user_id: uuid.UUID | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_token(user_id)}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHealth:
    def test_returns_200(self):
        client = TestClient(app)
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestAuthEndpoints:
    def test_register_creates_user(self):
        """POST /api/v1/auth/register should create a user and return UserOut."""
        # Responses: 1) email duplicate check → not found, 2) insert → new user row
        new_user = {**_FAKE_USER, "id": uuid.uuid4(), "role": "viewer"}
        responses = [
            _make_result(rows=[]),          # duplicate email check → none found
            _make_result(rows=[new_user]),  # INSERT RETURNING
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.post(
                "/api/v1/auth/register",
                json={"email": "new@vineguard.io", "password": "secret123"},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["email"] == new_user["email"]
            assert data["role"] == "viewer"
            assert data["is_active"] is True
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_login_returns_token(self):
        """POST /api/v1/auth/login with valid credentials returns a JWT."""
        responses = [
            _make_result(rows=[_FAKE_USER]),  # user lookup by email
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": _FAKE_USER["email"], "password": "secret123"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_login_wrong_password_returns_401(self):
        responses = [_make_result(rows=[_FAKE_USER])]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": _FAKE_USER["email"], "password": "wrong"},
            )
            assert resp.status_code == 401
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_login_unknown_email_returns_401(self):
        responses = [_make_result(rows=[])]  # user not found
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@example.com", "password": "secret123"},
            )
            assert resp.status_code == 401
        finally:
            app.dependency_overrides.pop(get_session, None)


class TestVineyardEndpoints:
    def test_list_vineyards_without_auth_returns_401(self):
        """GET /api/v1/vineyards without any auth header must return 401."""
        # Don't override session — the auth check happens first
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/vineyards")
        assert resp.status_code == 401

    def test_list_vineyards_with_api_key_returns_200(self):
        """GET /api/v1/vineyards with valid API key returns list."""
        # api_key_or_jwt passes on valid key; get_current_user inside the
        # route still needs a user lookup — provide the user row.
        responses = [
            _make_result(rows=[_FAKE_USER]),     # get_current_user lookup
            _make_result(rows=[_FAKE_VINEYARD]), # vineyards SELECT
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.get("/api/v1/vineyards", headers=AUTH_HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert data[0]["name"] == _FAKE_VINEYARD["name"]
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_list_vineyards_with_jwt_returns_200(self):
        """GET /api/v1/vineyards with Bearer JWT returns list."""
        responses = [
            _make_result(rows=[_FAKE_USER]),     # api_key_or_jwt → user lookup
            _make_result(rows=[_FAKE_USER]),     # get_current_user → user lookup
            _make_result(rows=[_FAKE_VINEYARD]), # vineyards SELECT
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.get("/api/v1/vineyards", headers=_jwt_headers())
            assert resp.status_code == 200
            data = resp.json()
            assert data[0]["name"] == _FAKE_VINEYARD["name"]
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_create_vineyard_with_operator_jwt(self):
        """POST /api/v1/vineyards with operator JWT creates a vineyard."""
        new_vineyard = {**_FAKE_VINEYARD, "id": uuid.uuid4()}
        responses = [
            _make_result(rows=[_FAKE_USER]),       # api_key_or_jwt
            _make_result(rows=[_FAKE_USER]),       # require_operator → get_current_user
            _make_result(rows=[new_vineyard]),     # INSERT RETURNING
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.post(
                "/api/v1/vineyards",
                json={"name": "New Yard", "region": "Sonoma", "owner_name": "Bob"},
                headers=_jwt_headers(),
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["name"] == new_vineyard["name"]
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_get_vineyard_not_found_returns_404(self):
        """GET /api/v1/vineyards/{id} for unknown ID returns 404."""
        responses = [
            _make_result(rows=[_FAKE_USER]),  # api_key_or_jwt
            _make_result(rows=[_FAKE_USER]),  # get_current_user
            _make_result(rows=[]),            # vineyard lookup → not found
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.get(f"/api/v1/vineyards/{uuid.uuid4()}", headers=_jwt_headers())
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_session, None)


class TestAlertEndpoints:
    def test_list_alerts_filters_by_is_active(self):
        """GET /api/v1/alerts?is_active=true returns only active alerts."""
        responses = [
            _make_result(rows=[_FAKE_USER]),   # api_key_or_jwt
            _make_result(rows=[_FAKE_USER]),   # get_current_user
            _make_result(rows=[_FAKE_ALERT]),  # alerts SELECT
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.get(
                "/api/v1/alerts",
                params={"is_active": "true"},
                headers=AUTH_HEADERS,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert all(a["is_active"] for a in data)
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_list_alerts_inactive(self):
        """GET /api/v1/alerts?is_active=false returns inactive alerts."""
        inactive_alert = {**_FAKE_ALERT, "is_active": False, "resolved_at": _NOW.isoformat()}
        responses = [
            _make_result(rows=[_FAKE_USER]),      # api_key_or_jwt
            _make_result(rows=[_FAKE_USER]),      # get_current_user
            _make_result(rows=[inactive_alert]),  # alerts SELECT
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.get(
                "/api/v1/alerts",
                params={"is_active": "false"},
                headers=AUTH_HEADERS,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert all(not a["is_active"] for a in data)
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_resolve_alert_requires_operator(self):
        """POST /api/v1/alerts/{id}/resolve with viewer role returns 403."""
        viewer_user = {**_FAKE_USER, "role": "viewer"}
        responses = [
            _make_result(rows=[viewer_user]),  # api_key_or_jwt
            _make_result(rows=[viewer_user]),  # require_operator → get_current_user
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.post(
                f"/api/v1/alerts/{_ALERT_ID}/resolve",
                headers=_jwt_headers(),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_resolve_alert_sets_inactive(self):
        """POST /api/v1/alerts/{id}/resolve resolves the alert."""
        resolved_alert = {**_FAKE_ALERT, "is_active": False, "resolved_at": _NOW}
        responses = [
            _make_result(rows=[_FAKE_USER]),         # api_key_or_jwt
            _make_result(rows=[_FAKE_USER]),         # require_operator → get_current_user
            _make_result(rows=[_FAKE_ALERT]),        # SELECT to verify exists
            _make_result(rows=[resolved_alert]),     # UPDATE RETURNING
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.post(
                f"/api/v1/alerts/{_ALERT_ID}/resolve",
                headers=_jwt_headers(),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_active"] is False
            assert data["resolved_at"] is not None
        finally:
            app.dependency_overrides.pop(get_session, None)


class TestBlockEndpoints:
    def test_get_block_with_nodes(self):
        """GET /api/v1/blocks/{id} returns BlockWithNodes."""
        responses = [
            _make_result(rows=[_FAKE_USER]),   # api_key_or_jwt
            _make_result(rows=[_FAKE_USER]),   # get_current_user
            _make_result(rows=[_FAKE_BLOCK]),  # block SELECT
            _make_result(rows=[_FAKE_NODE]),   # nodes SELECT
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.get(f"/api/v1/blocks/{_BLOCK_ID}", headers=AUTH_HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == str(_BLOCK_ID)
            assert isinstance(data["nodes"], list)
            assert data["nodes"][0]["device_id"] == _FAKE_NODE["device_id"]
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_get_block_not_found(self):
        """GET /api/v1/blocks/{id} for missing block returns 404."""
        responses = [
            _make_result(rows=[_FAKE_USER]),  # api_key_or_jwt
            _make_result(rows=[_FAKE_USER]),  # get_current_user
            _make_result(rows=[]),            # block SELECT → not found
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.get(f"/api/v1/blocks/{uuid.uuid4()}", headers=AUTH_HEADERS)
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_session, None)


class TestNodeEndpoints:
    def test_list_nodes_returns_200(self):
        """GET /api/v1/nodes returns list of nodes."""
        responses = [
            _make_result(rows=[_FAKE_USER]),  # api_key_or_jwt
            _make_result(rows=[_FAKE_USER]),  # get_current_user
            _make_result(rows=[_FAKE_NODE]),  # nodes SELECT
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.get("/api/v1/nodes", headers=AUTH_HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert data[0]["device_id"] == _FAKE_NODE["device_id"]
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_get_node_not_found(self):
        responses = [
            _make_result(rows=[_FAKE_USER]),  # api_key_or_jwt
            _make_result(rows=[_FAKE_USER]),  # get_current_user
            _make_result(rows=[]),            # node SELECT → not found
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.get(f"/api/v1/nodes/{uuid.uuid4()}", headers=AUTH_HEADERS)
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_session, None)


class TestRecommendationEndpoints:
    def test_list_recommendations_returns_200(self):
        responses = [
            _make_result(rows=[_FAKE_USER]),  # api_key_or_jwt
            _make_result(rows=[_FAKE_USER]),  # get_current_user
            _make_result(rows=[_FAKE_REC]),   # recommendations SELECT
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.get("/api/v1/recommendations", headers=AUTH_HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert data[0]["action_text"] == _FAKE_REC["action_text"]
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_acknowledge_recommendation(self):
        acked_rec = {**_FAKE_REC, "is_acknowledged": True, "acknowledged_at": _NOW}
        responses = [
            _make_result(rows=[_FAKE_USER]),   # api_key_or_jwt
            _make_result(rows=[_FAKE_USER]),   # require_operator
            _make_result(rows=[_FAKE_REC]),    # SELECT to verify exists
            _make_result(rows=[acked_rec]),    # UPDATE RETURNING
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            client = TestClient(app)
            resp = client.post(
                f"/api/v1/recommendations/{_REC_ID}/acknowledge",
                headers=_jwt_headers(),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_acknowledged"] is True
        finally:
            app.dependency_overrides.pop(get_session, None)
