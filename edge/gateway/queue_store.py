from __future__ import annotations

"""Disk-backed queue implementation using SQLite for message buffering."""

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Iterable, List
import sqlite3
import time


@dataclass(slots=True)
class QueueItem:
    id: int
    topic: str
    payload: str
    created_at: float


class PersistentQueue:
    """A small SQLite-backed persistent queue for MQTT messages."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = Lock()
        self._connection = sqlite3.connect(self._path, check_same_thread=False)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS queued_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        self._connection.commit()

    def enqueue(self, topic: str, payload: str) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT INTO queued_messages (topic, payload, created_at) VALUES (?, ?, ?)",
                (topic, payload, time.time()),
            )
            self._connection.commit()

    def get_batch(self, limit: int = 50) -> List[QueueItem]:
        with self._lock:
            cursor = self._connection.execute(
                "SELECT id, topic, payload, created_at FROM queued_messages ORDER BY id ASC LIMIT ?",
                (limit,),
            )
            rows = [QueueItem(*row) for row in cursor.fetchall()]
        return rows

    def remove(self, ids: Iterable[int]) -> None:
        ids_list = list(ids)
        if not ids_list:
            return
        with self._lock:
            self._connection.executemany("DELETE FROM queued_messages WHERE id = ?", ((i,) for i in ids_list))
            self._connection.commit()

    def count(self) -> int:
        with self._lock:
            cursor = self._connection.execute("SELECT COUNT(1) FROM queued_messages")
            (count,) = cursor.fetchone()
        return int(count)

    def close(self) -> None:
        with self._lock:
            self._connection.close()


__all__ = ["PersistentQueue", "QueueItem"]
