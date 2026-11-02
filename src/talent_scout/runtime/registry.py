import sqlite3
from datetime import UTC, datetime
from enum import StrEnum

import aiosqlite
from psycopg.errors import UndefinedColumn
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
  updated_at TEXT NOT NULL,
  customer_id TEXT
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
    customer_id: str | None = None
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

    async def run(self, sql: str, params: tuple = ()) -> list[dict]:
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
        await self.run(SCHEMA)
        try:
            await self.run("SELECT customer_id FROM runs LIMIT 0")
        except (sqlite3.OperationalError, UndefinedColumn):  # a table made before Customers existed
            await self.run("ALTER TABLE runs ADD COLUMN customer_id TEXT")

    async def insert(self, thread_id: str, request_text: str, customer_id: str | None = None) -> None:
        now = _now()
        await self.run(
            "INSERT INTO runs (thread_id, summary, status, created_at, updated_at, customer_id) VALUES (?, ?, ?, ?, ?, ?)",
            (thread_id, request_text[:80], RunStatus.running.value, now, now, customer_id),
        )

    async def delete(self, thread_id: str) -> None:
        await self.run("DELETE FROM runs WHERE thread_id = ?", (thread_id,))

    async def transition(self, thread_id: str, status: RunStatus, error: str | None = None) -> None:
        # One UPDATE, never a read then a write, so two processes can't interleave a transition.
        await self.run(
            "UPDATE runs SET status = ?, error = ?, updated_at = ? WHERE thread_id = ?",
            (status.value, error, _now(), thread_id),
        )

    async def reconcile(self, thread_id: str, status: RunStatus, error: str | None) -> None:
        # Only a still-running row: another process may have moved it since the lock probe.
        await self.run(
            "UPDATE runs SET status = ?, error = ?, updated_at = ? WHERE thread_id = ? AND status = ?",
            (status.value, error, _now(), thread_id, RunStatus.running.value),
        )

    async def get(self, thread_id: str) -> RunRecord | None:
        rows = await self.run("SELECT * FROM runs WHERE thread_id = ?", (thread_id,))
        return RunRecord.model_validate(rows[0]) if rows else None

    async def list_all(self, csm_id: str | None = None, customer_id: str | None = None) -> list[RunRecord]:
        where, params = [], []
        if customer_id:
            where.append("customer_id = ?")
            params.append(customer_id)
        if csm_id:
            where.append("customer_id IN (SELECT id FROM customers WHERE csm_id = ?)")
            params.append(csm_id)
        clause = f" WHERE {' AND '.join(where)}" if where else ""
        rows = await self.run(f"SELECT * FROM runs{clause} ORDER BY created_at DESC", tuple(params))
        return [RunRecord.model_validate(row) for row in rows]
