from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return bcrypt hash of *password*."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, secret: str, algorithm: str, ttl_seconds: int) -> str:
    """Create a signed JWT containing *data* that expires in *ttl_seconds*."""
    to_encode = data.copy()
    expire = datetime.now(tz=timezone.utc) + timedelta(seconds=ttl_seconds)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, secret, algorithm=algorithm)


def decode_token(token: str, secret: str, algorithm: str) -> dict:
    """Decode and verify a JWT.  Raises :class:`jose.JWTError` if invalid."""
    return jwt.decode(token, secret, algorithms=[algorithm])
