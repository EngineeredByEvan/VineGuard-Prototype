from pydantic import BaseModel
from uuid import UUID
from typing import Any


class CommandRequest(BaseModel):
    node_id: UUID
    command: str
    payload: dict[str, Any] | None = None
