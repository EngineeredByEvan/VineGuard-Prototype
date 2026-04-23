from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...auth import create_access_token, hash_password, verify_password
from ...database import get_session
from ... import models, schemas
from ...dependencies import get_api_settings
from ...config import ApiSettings

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=schemas.TokenResponse)
async def login(
    payload: schemas.LoginRequest,
    settings: ApiSettings = Depends(get_api_settings),
    session: AsyncSession = Depends(get_session),
) -> schemas.TokenResponse:
    """Authenticate with email + password and return a JWT bearer token."""
    result = await session.execute(
        select(models.users).where(models.users.c.email == payload.email)
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = row._mapping
    if not user["is_active"] or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        data={"sub": str(user["id"])},
        secret=settings.security.jwt_secret,
        algorithm=settings.security.jwt_algorithm,
        ttl_seconds=settings.security.jwt_ttl_seconds,
    )
    return schemas.TokenResponse(access_token=token)


@router.post("/auth/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: schemas.UserCreate,
    session: AsyncSession = Depends(get_session),
) -> schemas.UserOut:
    """Register a new user account (open registration, default role = viewer)."""
    # Check for duplicate email
    existing = await session.execute(
        select(models.users).where(models.users.c.email == payload.email)
    )
    if existing.fetchone() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    allowed_roles = {"admin", "operator", "viewer"}
    role = payload.role if payload.role in allowed_roles else "viewer"

    result = await session.execute(
        models.users.insert().values(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            role=role,
            is_active=True,
        ).returning(*models.users.c)
    )
    await session.commit()
    row = result.fetchone()
    return schemas.UserOut(**row._mapping)
