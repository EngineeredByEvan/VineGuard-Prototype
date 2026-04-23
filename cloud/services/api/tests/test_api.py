"""
VineGuard API tests.

Uses FastAPI TestClient with dependency overrides so no real DB or Redis is
needed.  The session dependency is replaced by a lightweight async mock that
records calls and returns pre-baked rows for each sequential execute() call.

Dependency call order per request
----------------------------------
API-key path (X-API-Key header):
    api_key_or_jwt       → validates key, returns immediately (no DB)
    get_current_user     → 1 × session.execute()   [route dependency]
    route body           → N × session.execute()

JWT (Bearer) path:
    api_key_or_jwt       → 1 × session.execute()   [user lookup in JWT path]
    get_current_user     → 1 × session.execute()
    route body           → N × session.execute()

For operator/admin routes that use require_operator instead of get_current_user:
    api_key_or_jwt       → 1 × session.execute()   (JWT) or 0 (API key)
    require_operator
      └─ get_current_user→ 1 × session.execute()
    route body           → N × session.execute()
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import os

# Set env vars BEFORE importing app so pydantic-settings can build ApiSettings
os.environ.setdefault("API_SECURITY__API_KEY", "test-api-key-1234567890abcdef")
os.environ.setdefault("API_SECURITY__JWT_SECRET", "test-jwt-secret-that-is-long-enough-for-hs256")
os.environ.setdefault("API_SECURITY__JWT_ALGORITHM", "HS256")
os.environ.setdefault("API_SECURITY__JWT_TTL_SECONDS", "3600")
os.environ.setdefault("API_DATABASE__DSN", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("API_REDIS__URL", "redis://localhost:6379/0")

from app.main import app  # noqa: E402
from app import schemas  # noqa: E402
from app.auth import create_access_token, hash_password  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.database import get_session  # noqa: E402

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

SETTINGS = get_settings()
API_KEY = SETTINGS.security.api_key
API_KEY_HEADERS = {"X-API-Key": API_KEY}

_USER_ID = uuid.uuid4()
_VINEYARD_ID = uuid.uuid4()
_BLOCK_ID = uuid.uuid4()
_NODE_ID = uuid.uuid4()
_ALERT_ID = uuid.uuid4()
_REC_ID = uuid.uuid4()

_NOW = datetime.now(tz=timezone.utc)

# Hash computed once at import time (bcrypt 4.x + passlib)
_HASHED_PW = hash_password("secret123")

_FAKE_USER_OPERATOR = {
    "id": _USER_ID,
    "email": "operator@vineguard.io",
    "hashed_password": _HASHED_PW,
    "role": "operator",
    "is_active": True,
    "created_at": _NOW,
}

_FAKE_USER_VIEWER = {
    "id": uuid.uuid4(),
    "email": "viewer@vineguard.io",
    "hashed_password": _HASHED_PW,
    "role": "viewer",
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


# ---------------------------------------------------------------------------
# Mock DB session
# ---------------------------------------------------------------------------

def _make_row(data: dict) -> MagicMock:
    row = MagicMock()
    row._mapping = data
    return row


def _make_result(rows: list[dict] | None = None, scalar: Any = None) -> MagicMock:
    result = MagicMock()
    if rows is not None:
        mock_rows = [_make_row(r) for r in rows]
        result.fetchall.return_value = mock_rows
        result.fetchone.return_value = mock_rows[0] if mock_rows else None
    else:
        result.fetchall.return_value = []
        result.fetchone.return_value = None
    result.scalar.return_value = scalar if scalar is not None else 0
    return result


class MockSession:
    """Sequential async session mock.

    All dependency injection points within one request share the same instance,
    so the response index advances correctly across calls.
    """

    def __init__(self, responses: list[MagicMock]) -> None:
        self._responses = list(responses)
        self._idx = 0

    async def execute(self, *args: Any, **kwargs: Any) -> MagicMock:
        if self._idx < len(self._responses):
            result = self._responses[self._idx]
        else:
            result = _make_result()
        self._idx += 1
        return result

    async def commit(self) -> None:
        pass

    async def __aenter__(self) -> "MockSession":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


def _session_override(responses: list[MagicMock]):
    """Dependency override that yields a SHARED MockSession for every injected
    call within a single request so the sequential index is maintained."""
    shared = MockSession(responses)

    async def _dep() -> AsyncIterator[MockSession]:
        yield shared

    return _dep


# ---------------------------------------------------------------------------
# JWT helpers
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
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_returns_200(self):
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Auth endpoints (no global auth dependency — they are public)
# ---------------------------------------------------------------------------

class TestAuthEndpoints:
    def test_register_creates_user(self):
        """POST /api/v1/auth/register returns 201 with UserOut."""
        new_user = {**_FAKE_USER_VIEWER, "id": uuid.uuid4()}
        responses = [
            _make_result(rows=[]),         # email duplicate check → none found
            _make_result(rows=[new_user]), # INSERT RETURNING
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).post(
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
        """POST /api/v1/auth/login with correct credentials returns JWT."""
        responses = [_make_result(rows=[_FAKE_USER_OPERATOR])]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).post(
                "/api/v1/auth/login",
                json={"email": _FAKE_USER_OPERATOR["email"], "password": "secret123"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_login_wrong_password_returns_401(self):
        responses = [_make_result(rows=[_FAKE_USER_OPERATOR])]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).post(
                "/api/v1/auth/login",
                json={"email": _FAKE_USER_OPERATOR["email"], "password": "wrongpassword"},
            )
            assert resp.status_code == 401
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_login_unknown_email_returns_401(self):
        responses = [_make_result(rows=[])]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).post(
                "/api/v1/auth/login",
                json={"email": "ghost@example.com", "password": "secret123"},
            )
            assert resp.status_code == 401
        finally:
            app.dependency_overrides.pop(get_session, None)


# ---------------------------------------------------------------------------
# Vineyard endpoints
# ---------------------------------------------------------------------------

class TestVineyardEndpoints:
    def test_list_vineyards_without_auth_returns_401(self):
        """No auth header → 401 (api_key_or_jwt rejects)."""
        from fastapi.testclient import TestClient
        resp = TestClient(app, raise_server_exceptions=False).get("/api/v1/vineyards")
        assert resp.status_code == 401

    def test_list_vineyards_with_api_key_returns_200(self):
        """Valid API key → api_key_or_jwt and get_current_user both short-circuit (no DB).
        Only the route body issues a query: vineyards SELECT(DB#0).
        """
        responses = [
            _make_result(rows=[_FAKE_VINEYARD]),  # vineyards SELECT
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).get("/api/v1/vineyards", headers=API_KEY_HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert data[0]["name"] == _FAKE_VINEYARD["name"]
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_list_vineyards_with_jwt_returns_200(self):
        """Valid JWT → api_key_or_jwt(DB#0 user lookup), get_current_user(DB#1), SELECT(DB#2)."""
        responses = [
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # api_key_or_jwt user lookup
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # get_current_user
            _make_result(rows=[_FAKE_VINEYARD]),        # vineyards SELECT
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).get("/api/v1/vineyards", headers=_jwt_headers())
            assert resp.status_code == 200
            data = resp.json()
            assert data[0]["name"] == _FAKE_VINEYARD["name"]
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_create_vineyard_with_operator_jwt(self):
        """POST /api/v1/vineyards with operator JWT creates a vineyard (201)."""
        new_vineyard = {**_FAKE_VINEYARD, "id": uuid.uuid4(), "name": "New Yard"}
        responses = [
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # api_key_or_jwt
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # require_operator → get_current_user
            _make_result(rows=[new_vineyard]),          # INSERT RETURNING
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).post(
                "/api/v1/vineyards",
                json={"name": "New Yard", "region": "Sonoma", "owner_name": "Bob"},
                headers=_jwt_headers(),
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["name"] == "New Yard"
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_get_vineyard_not_found_returns_404(self):
        """GET /api/v1/vineyards/{unknown} → 404."""
        responses = [
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # api_key_or_jwt
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # get_current_user
            _make_result(rows=[]),                      # vineyard SELECT → not found
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).get(f"/api/v1/vineyards/{uuid.uuid4()}", headers=_jwt_headers())
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_session, None)


# ---------------------------------------------------------------------------
# Alert endpoints
# ---------------------------------------------------------------------------

class TestAlertEndpoints:
    def test_list_alerts_filters_by_is_active_true(self):
        """GET /api/v1/alerts?is_active=true returns active alerts (API key path).
        API key → no DB for auth; only route body issues a query.
        """
        responses = [
            _make_result(rows=[_FAKE_ALERT]),  # alerts SELECT
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).get(
                "/api/v1/alerts",
                params={"is_active": "true"},
                headers=API_KEY_HEADERS,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert all(a["is_active"] for a in data)
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_list_alerts_filters_by_is_active_false(self):
        """GET /api/v1/alerts?is_active=false returns resolved alerts."""
        inactive_alert = {**_FAKE_ALERT, "is_active": False, "resolved_at": _NOW}
        responses = [
            _make_result(rows=[inactive_alert]),  # alerts SELECT
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).get(
                "/api/v1/alerts",
                params={"is_active": "false"},
                headers=API_KEY_HEADERS,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert all(not a["is_active"] for a in data)
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_resolve_alert_requires_operator(self):
        """POST /api/v1/alerts/{id}/resolve with viewer role → 403."""
        responses = [
            _make_result(rows=[_FAKE_USER_VIEWER]),  # api_key_or_jwt
            _make_result(rows=[_FAKE_USER_VIEWER]),  # require_operator → get_current_user
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).post(
                f"/api/v1/alerts/{_ALERT_ID}/resolve",
                headers=_jwt_headers(_FAKE_USER_VIEWER["id"]),
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_resolve_alert_sets_inactive(self):
        """POST /api/v1/alerts/{id}/resolve with operator JWT → 200, is_active=False."""
        resolved_alert = {**_FAKE_ALERT, "is_active": False, "resolved_at": _NOW}
        responses = [
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # api_key_or_jwt
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # require_operator → get_current_user
            _make_result(rows=[_FAKE_ALERT]),           # SELECT to verify alert exists
            _make_result(rows=[resolved_alert]),        # UPDATE RETURNING
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).post(
                f"/api/v1/alerts/{_ALERT_ID}/resolve",
                headers=_jwt_headers(),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_active"] is False
            assert data["resolved_at"] is not None
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_resolve_alert_not_found(self):
        """POST /api/v1/alerts/{unknown}/resolve → 404."""
        responses = [
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # api_key_or_jwt
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # require_operator
            _make_result(rows=[]),                      # alert SELECT → not found
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).post(
                f"/api/v1/alerts/{uuid.uuid4()}/resolve",
                headers=_jwt_headers(),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_session, None)


# ---------------------------------------------------------------------------
# Block endpoints
# ---------------------------------------------------------------------------

class TestBlockEndpoints:
    def test_get_block_with_nodes(self):
        """GET /api/v1/blocks/{id} returns BlockWithNodes including node list.
        API key → no auth DB calls.
        """
        responses = [
            _make_result(rows=[_FAKE_BLOCK]),  # block SELECT
            _make_result(rows=[_FAKE_NODE]),   # nodes SELECT
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).get(f"/api/v1/blocks/{_BLOCK_ID}", headers=API_KEY_HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == str(_BLOCK_ID)
            assert isinstance(data["nodes"], list)
            assert data["nodes"][0]["device_id"] == _FAKE_NODE["device_id"]
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_get_block_not_found(self):
        """GET /api/v1/blocks/{unknown} → 404."""
        responses = [
            _make_result(rows=[]),  # block SELECT → not found
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).get(f"/api/v1/blocks/{uuid.uuid4()}", headers=API_KEY_HEADERS)
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_create_block_operator(self):
        """POST /api/v1/blocks with operator JWT creates block."""
        new_block = {**_FAKE_BLOCK, "id": uuid.uuid4(), "name": "Block B"}
        responses = [
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # api_key_or_jwt
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # require_operator
            _make_result(rows=[_FAKE_VINEYARD]),        # vineyard exists check
            _make_result(rows=[new_block]),             # INSERT RETURNING
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).post(
                "/api/v1/blocks",
                json={
                    "vineyard_id": str(_VINEYARD_ID),
                    "name": "Block B",
                    "variety": "Pinot Noir",
                },
                headers=_jwt_headers(),
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["name"] == "Block B"
        finally:
            app.dependency_overrides.pop(get_session, None)


# ---------------------------------------------------------------------------
# Node endpoints
# ---------------------------------------------------------------------------

class TestNodeEndpoints:
    def test_list_nodes_returns_200(self):
        """GET /api/v1/nodes returns list of nodes (API key → no auth DB calls)."""
        responses = [
            _make_result(rows=[_FAKE_NODE]),  # nodes SELECT
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).get("/api/v1/nodes", headers=API_KEY_HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert data[0]["device_id"] == _FAKE_NODE["device_id"]
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_get_node_not_found(self):
        """GET /api/v1/nodes/{unknown} → 404."""
        responses = [
            _make_result(rows=[]),  # node SELECT → not found
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).get(f"/api/v1/nodes/{uuid.uuid4()}", headers=API_KEY_HEADERS)
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_provision_node_operator(self):
        """POST /api/v1/nodes with operator JWT → 201."""
        new_node = {**_FAKE_NODE, "id": uuid.uuid4(), "device_id": "dev-new-999"}
        responses = [
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # api_key_or_jwt
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # require_operator
            _make_result(rows=[_FAKE_BLOCK]),           # block exists check
            _make_result(rows=[]),                      # duplicate device_id check → not found
            _make_result(rows=[new_node]),              # INSERT RETURNING
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).post(
                "/api/v1/nodes",
                json={
                    "block_id": str(_BLOCK_ID),
                    "device_id": "dev-new-999",
                    "name": "New Node",
                },
                headers=_jwt_headers(),
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["device_id"] == "dev-new-999"
        finally:
            app.dependency_overrides.pop(get_session, None)


# ---------------------------------------------------------------------------
# Recommendation endpoints
# ---------------------------------------------------------------------------

class TestRecommendationEndpoints:
    def test_list_recommendations_returns_200(self):
        """GET /api/v1/recommendations returns list (API key → no auth DB calls)."""
        responses = [
            _make_result(rows=[_FAKE_REC]),  # recommendations SELECT
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).get("/api/v1/recommendations", headers=API_KEY_HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert data[0]["action_text"] == _FAKE_REC["action_text"]
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_acknowledge_recommendation(self):
        """POST /api/v1/recommendations/{id}/acknowledge → 200, is_acknowledged=True."""
        acked_rec = {**_FAKE_REC, "is_acknowledged": True, "acknowledged_at": _NOW}
        responses = [
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # api_key_or_jwt
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # require_operator
            _make_result(rows=[_FAKE_REC]),             # SELECT to verify exists
            _make_result(rows=[acked_rec]),             # UPDATE RETURNING
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).post(
                f"/api/v1/recommendations/{_REC_ID}/acknowledge",
                headers=_jwt_headers(),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_acknowledged"] is True
        finally:
            app.dependency_overrides.pop(get_session, None)

    def test_acknowledge_rec_not_found(self):
        """POST /api/v1/recommendations/{unknown}/acknowledge → 404."""
        responses = [
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # api_key_or_jwt
            _make_result(rows=[_FAKE_USER_OPERATOR]),  # require_operator
            _make_result(rows=[]),                      # rec SELECT → not found
        ]
        app.dependency_overrides[get_session] = _session_override(responses)
        try:
            from fastapi.testclient import TestClient
            resp = TestClient(app).post(
                f"/api/v1/recommendations/{uuid.uuid4()}/acknowledge",
                headers=_jwt_headers(),
            )
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.pop(get_session, None)
