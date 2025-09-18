from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID

from app.core.security import decode_token
from app.db.session import get_db


security = HTTPBearer(auto_error=False)


def _get_user_by_id(db: Session, user_id: UUID):
    query = text(
        """
        SELECT id, org_id, email, role, created_at
        FROM users
        WHERE id = :user_id
        """
    )
    result = db.execute(query, {"user_id": str(user_id)}).mappings().first()
    return result


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    org_id = payload.get("org_id")
    if user_id is None or org_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    db_user = _get_user_by_id(db, UUID(user_id))
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return {"user_id": UUID(user_id), "org_id": UUID(org_id), "role": db_user["role"], "email": db_user["email"]}
