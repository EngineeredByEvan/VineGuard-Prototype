from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _create_token(data: Dict[str, Any], expires_delta: timedelta) -> tuple[str, datetime]:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(tz=timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt, expire


def create_access_token(subject: str, org_id: str, role: str) -> tuple[str, datetime]:
    settings = get_settings()
    claims = {"sub": subject, "org": org_id, "role": role, "type": "access"}
    expires = timedelta(minutes=settings.access_token_expires_min)
    return _create_token(claims, expires)


def create_refresh_token(subject: str, org_id: str, role: str) -> tuple[str, datetime]:
    settings = get_settings()
    claims = {"sub": subject, "org": org_id, "role": role, "type": "refresh"}
    expires = timedelta(hours=settings.refresh_token_expires_hours)
    return _create_token(claims, expires)


def decode_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    return payload
