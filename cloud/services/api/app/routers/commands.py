import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from paho.mqtt import publish
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.commands import CommandRequest

settings = get_settings()
router = APIRouter(prefix="/commands", tags=["commands"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def enqueue_command(
    payload: CommandRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    node = db.execute(
        text("SELECT id FROM nodes WHERE id = :id AND org_id = :org_id"),
        {"id": str(payload.node_id), "org_id": str(current_user["org_id"])},
    ).first()
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")

    topic = f"org/{current_user['org_id']}/nodes/{payload.node_id}/commands"
    message = json.dumps(
        {
            "command": payload.command,
            "payload": payload.payload or {},
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    auth = None
    if settings.mqtt_username:
        auth = {"username": settings.mqtt_username, "password": settings.mqtt_password or ""}

    publish.single(
        topic,
        payload=message,
        hostname=settings.mqtt_host,
        port=settings.mqtt_port,
        auth=auth,
    )

    return {"status": "queued", "topic": topic}
