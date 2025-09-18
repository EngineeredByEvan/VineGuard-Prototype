from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def create_token(subject: Dict[str, Any], expires_delta: timedelta) -> str:
    payload = subject.copy()
    expire = datetime.now(tz=timezone.utc) + expires_delta
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: UUID, org_id: UUID, role: str) -> str:
    return create_token(
        {"sub": str(user_id), "org_id": str(org_id), "role": role, "type": "access"},
        timedelta(minutes=settings.access_token_expires_minutes),
    )


def create_refresh_token(user_id: UUID, org_id: UUID) -> str:
    return create_token(
        {"sub": str(user_id), "org_id": str(org_id), "type": "refresh"},
        timedelta(minutes=settings.refresh_token_expires_minutes),
    )


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)
