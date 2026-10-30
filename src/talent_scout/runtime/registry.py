import sqlite3
from datetime import UTC, datetime
from enum import StrEnum

import aiosqlite

from talent_scout.kernel.types import Model

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  thread_id  TEXT PRIMARY KEY,
  summary    TEXT NOT NULL,
  status     TEXT NOT NULL,
  error      TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)
"""


class RunStatus(StrEnum):
    running = "running"
    paused = "paused"
    done = "done"
    aborted = "aborted"
    failed = "failed"


class RunRecord(Model):
    thread_id: str
    summary: str
    status: RunStatus
    error: str | None
    created_at: datetime
    updated_at: datetime


def derive_status(snapshot) -> tuple[RunStatus, str | None]:
    if snapshot.interrupts:
        return RunStatus.paused, None
    if snapshot.next:
        return RunStatus.failed, "process stopped mid-Run"
    if not snapshot.values:
        return RunStatus.aborted, "killed before the first checkpoint"
    if snapshot.values.get("brief"):
        return RunStatus.done, None
    return RunStatus.aborted, None


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Registry:
    """An index over Runs: the checkpoint is the truth, and this lags it but never leads it."""

    def __init__(self, conn: aiosqlite.Connection):
        conn.row_factory = sqlite3.Row
        self._conn = conn

    async def setup(self) -> None:
        await self._conn.execute(SCHEMA)
        await self._conn.commit()

    async def insert(self, thread_id: str, request_text: str) -> None:
        now = _now()
        await self._conn.execute(
            "INSERT INTO runs (thread_id, summary, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (thread_id, request_text[:80], RunStatus.running, now, now),
        )
        await self._conn.commit()

    async def transition(self, thread_id: str, status: RunStatus, error: str | None = None) -> None:
        # One UPDATE, never a read then a write, so two processes can't interleave a transition.
        await self._conn.execute(
            "UPDATE runs SET status = ?, error = ?, updated_at = ? WHERE thread_id = ?",
            (status, error, _now(), thread_id),
        )
        await self._conn.commit()

    async def get(self, thread_id: str) -> RunRecord | None:
        async with self._conn.execute("SELECT * FROM runs WHERE thread_id = ?", (thread_id,)) as cursor:
            row = await cursor.fetchone()
        return RunRecord.model_validate(dict(row)) if row else None
