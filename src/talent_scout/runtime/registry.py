import sqlite3
from datetime import UTC, datetime
from enum import StrEnum

import aiosqlite
from psycopg_pool import AsyncConnectionPool

from talent_scout.kernel.types import Model

# Plain TEXT columns and `?` placeholders, so the same statements run on SQLite and, with `%s`, on Postgres.
# ponytail: created if missing at startup, no migrations; add Alembic when a column has to change.
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


RESUMABLE = (RunStatus.paused, RunStatus.failed)


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

    def __init__(self, db: aiosqlite.Connection | AsyncConnectionPool):
        if isinstance(db, aiosqlite.Connection):
            db.row_factory = sqlite3.Row
        self._db = db

    async def _run(self, sql: str, params: tuple = ()) -> list[dict]:
        # One statement per call, so each commits alone on either database.
        if isinstance(self._db, AsyncConnectionPool):
            async with self._db.connection() as conn:
                cursor = await conn.execute(sql.replace("?", "%s"), params)
                return await cursor.fetchall() if cursor.description else []
        async with self._db.execute(sql, params) as cursor:
            rows = [dict(row) for row in await cursor.fetchall()]
        await self._db.commit()
        return rows

    async def setup(self) -> None:
        await self._run(SCHEMA)

    async def insert(self, thread_id: str, request_text: str) -> None:
        now = _now()
        await self._run(
            "INSERT INTO runs (thread_id, summary, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (thread_id, request_text[:80], RunStatus.running.value, now, now),
        )

    async def transition(self, thread_id: str, status: RunStatus, error: str | None = None) -> None:
        # One UPDATE, never a read then a write, so two processes can't interleave a transition.
        await self._run(
            "UPDATE runs SET status = ?, error = ?, updated_at = ? WHERE thread_id = ?",
            (status.value, error, _now(), thread_id),
        )

    async def reconcile(self, thread_id: str, status: RunStatus, error: str | None) -> None:
        # Only a still-running row: another process may have moved it since the lock probe.
        await self._run(
            "UPDATE runs SET status = ?, error = ?, updated_at = ? WHERE thread_id = ? AND status = ?",
            (status.value, error, _now(), thread_id, RunStatus.running.value),
        )

    async def get(self, thread_id: str) -> RunRecord | None:
        rows = await self._run("SELECT * FROM runs WHERE thread_id = ?", (thread_id,))
        return RunRecord.model_validate(rows[0]) if rows else None

    async def list_all(self) -> list[RunRecord]:
        rows = await self._run("SELECT * FROM runs ORDER BY created_at DESC")
        return [RunRecord.model_validate(row) for row in rows]
