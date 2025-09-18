from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user_exists = db.execute(text("SELECT 1 FROM users WHERE email = :email"), {"email": payload.email}).first()
    if user_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    org_id = uuid4()
    user_id = uuid4()

    db.execute(
        text("INSERT INTO orgs (id, name, created_at) VALUES (:id, :name, :created_at)"),
        {"id": str(org_id), "name": payload.org_name, "created_at": datetime.now(timezone.utc)},
    )

    db.execute(
        text(
            """
            INSERT INTO users (id, org_id, email, password_hash, role, created_at)
            VALUES (:id, :org_id, :email, :password_hash, 'admin', :created_at)
            """
        ),
        {
            "id": str(user_id),
            "org_id": str(org_id),
            "email": payload.email,
            "password_hash": hash_password(payload.password),
            "created_at": datetime.now(timezone.utc),
        },
    )

    db.commit()

    access = create_access_token(user_id=user_id, org_id=org_id, role="admin")
    refresh = create_refresh_token(user_id=user_id, org_id=org_id)

    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expires_minutes * 60,
        refresh_expires_in=settings.refresh_token_expires_minutes * 60,
    )


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    query = text("SELECT id, org_id, password_hash, role FROM users WHERE email = :email")
    record = db.execute(query, {"email": payload.email}).mappings().first()
    if record is None or not verify_password(payload.password, record["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access = create_access_token(user_id=record["id"], org_id=record["org_id"], role=record["role"])
    refresh = create_refresh_token(user_id=record["id"], org_id=record["org_id"])

    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expires_minutes * 60,
        refresh_expires_in=settings.refresh_token_expires_minutes * 60,
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        decoded = decode_token(payload.refresh_token)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = decoded.get("sub")
    org_id = decoded.get("org_id")
    if user_id is None or org_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed refresh token")

    record = db.execute(
        text("SELECT role FROM users WHERE id = :id"),
        {"id": user_id},
    ).mappings().first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access = create_access_token(user_id=user_id, org_id=org_id, role=record["role"])
    refresh_token = create_refresh_token(user_id=user_id, org_id=org_id)

    return TokenPair(
        access_token=access,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expires_minutes * 60,
        refresh_expires_in=settings.refresh_token_expires_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
def me(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.execute(
        text("SELECT id, org_id, email, role, created_at FROM users WHERE id = :id"),
        {"id": str(current_user["user_id"])},
    ).mappings().first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse(**record)
