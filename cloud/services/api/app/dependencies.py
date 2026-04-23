from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException, Query, status
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas
from .auth import decode_token, verify_password
from .config import ApiSettings, get_settings
from .database import get_session


async def get_api_settings() -> ApiSettings:
    return get_settings()


# ---------------------------------------------------------------------------
# API-key auth (legacy — used by /readings, /streams/telemetry)
# ---------------------------------------------------------------------------

async def api_key_auth(
    x_api_key: str | None = Header(default=None),
    api_key_query: str | None = Query(default=None, alias="api_key"),
    settings: ApiSettings = Depends(get_api_settings),
) -> None:
    """Accept either X-API-Key header or ?api_key= query param."""
    candidate = x_api_key or api_key_query
    if candidate != settings.security.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

_API_KEY_USER = schemas.UserOut(
    id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
    email="apikey@system",
    role="admin",
    is_active=True,
)


async def get_current_user(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    api_key_query: str | None = Query(default=None, alias="api_key"),
    settings: ApiSettings = Depends(get_api_settings),
    session: AsyncSession = Depends(get_session),
) -> schemas.UserOut:
    """Return the current user.

    Accepts either a Bearer JWT (full user lookup) or a valid API key
    (returns a synthetic admin user so API-key callers can use all routes).
    Raises HTTP 401 if neither credential is valid.
    """
    # 1. Try API key first (no DB round-trip needed)
    candidate = x_api_key or api_key_query
    if candidate is not None and candidate == settings.security.api_key:
        return _API_KEY_USER

    # 2. Try Bearer JWT
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not authorization:
        raise credentials_exc

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise credentials_exc

    try:
        payload = decode_token(
            token,
            settings.security.jwt_secret,
            settings.security.jwt_algorithm,
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    result = await session.execute(
        select(models.users).where(models.users.c.id == user_id)
    )
    row = result.fetchone()
    if row is None or not row._mapping["is_active"]:
        raise credentials_exc

    return schemas.UserOut(**row._mapping)


async def require_operator(
    current_user: schemas.UserOut = Depends(get_current_user),
) -> schemas.UserOut:
    """Require role = operator or admin."""
    if current_user.role not in ("operator", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator or admin role required",
        )
    return current_user


async def require_admin(
    current_user: schemas.UserOut = Depends(get_current_user),
) -> schemas.UserOut:
    """Require role = admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


# ---------------------------------------------------------------------------
# Combined API-key OR JWT dependency (used by v1 routers)
# ---------------------------------------------------------------------------

async def api_key_or_jwt(
    x_api_key: str | None = Header(default=None),
    api_key_query: str | None = Query(default=None, alias="api_key"),
    authorization: str | None = Header(default=None),
    settings: ApiSettings = Depends(get_api_settings),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Accept either a valid X-API-Key / ?api_key= OR a valid Bearer JWT."""
    # 1. Try API key first
    candidate = x_api_key or api_key_query
    if candidate is not None:
        if candidate == settings.security.api_key:
            return
        # A key was provided but it is wrong — fall through to JWT attempt
        # only if there is also an Authorization header; otherwise fail fast.
        if authorization is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

    # 2. Try Bearer JWT
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            try:
                payload = decode_token(
                    token,
                    settings.security.jwt_secret,
                    settings.security.jwt_algorithm,
                )
                user_id: str | None = payload.get("sub")
                if user_id:
                    result = await session.execute(
                        select(models.users).where(models.users.c.id == user_id)
                    )
                    row = result.fetchone()
                    if row is not None and row._mapping["is_active"]:
                        return
            except JWTError:
                pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------

async def get_redis(settings: ApiSettings = Depends(get_api_settings)) -> AsyncIterator[Redis]:
    redis = Redis.from_url(settings.redis.url)
    try:
        yield redis
    finally:
        await redis.aclose()
