import shutil
import sqlite3
import tempfile
from itertools import groupby
from pathlib import Path

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from talent_scout.kernel.settings import Settings

# Written by scripts/export_seed.py; the columns must match the live tables.
TABLES = ("checkpoints", "writes", "runs", "customers", "customer_profiles")
KEYS = {"runs": "thread_id", "customers": "id", "customer_profiles": "customer_id", "seeded": "thread_id"}


async def _insert(run, table: str, row: dict) -> None:
    cols = ",".join(row)
    await run(
        f"INSERT INTO {table} ({cols}) VALUES ({','.join('?' * len(row))}) ON CONFLICT ({KEYS[table]}) DO NOTHING",
        tuple(row.values()),
    )


async def seed_runs(settings: Settings, saver, run) -> None:
    """Copy the sample Runs in seed_dir into this install once each, so one deleted here stays deleted."""
    src = settings.seed_dir
    if src is None or not (src / "seed.sqlite").is_file():
        return
    await run("CREATE TABLE IF NOT EXISTS seeded (thread_id TEXT PRIMARY KEY)")
    done = {r["thread_id"] for r in await run("SELECT thread_id FROM seeded")}
    # A copy, because the sqlite saver switches the file it opens to WAL.
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "seed.sqlite"
        shutil.copy(src / "seed.sqlite", path)
        async with aiosqlite.connect(path) as db:
            db.row_factory = sqlite3.Row
            rows = {t: [dict(r) for r in await db.execute_fetchall(f"SELECT * FROM {t}")] for t in ("runs", "customers", "customer_profiles")}
            new = [r for r in rows["runs"] if r["thread_id"] not in done]
            owners = {r["customer_id"] for r in new}
            for table in ("customers", "customer_profiles"):
                for row in rows[table]:
                    if row[KEYS[table]] in owners:
                        await _insert(run, table, row)
            # Through the savers, so the same seed loads into SQLite or Postgres; the serializer must match the live one.
            seed = AsyncSqliteSaver(db, serde=saver.serde)
            for row in new:
                thread_id = row["thread_id"]
                found = await seed.aget_tuple({"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}})
                config = await saver.aput(
                    {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}},
                    found.checkpoint, found.metadata, found.checkpoint["channel_versions"],
                )
                for task_id, writes in groupby(found.pending_writes or [], key=lambda w: w[0]):
                    await saver.aput_writes(config, [(channel, value) for _, channel, value in writes], task_id)
                await _insert(run, "runs", row)
                if (briefs := src / "briefs" / thread_id).is_dir():
                    shutil.copytree(briefs, settings.runs_dir / thread_id, dirs_exist_ok=True)
                await _insert(run, "seeded", {"thread_id": thread_id})
