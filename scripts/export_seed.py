"""Pack finished local Runs into seed/ so a fresh deploy starts with them.

Usage: uv run python scripts/export_seed.py THREAD_ID [THREAD_ID ...]
Only each Run's last checkpoint is kept: that is all the Brief and the log need.
"""
import shutil
import sqlite3
import sys
from pathlib import Path

from talent_scout.kernel.settings import get_settings
from talent_scout.runtime.seed import TABLES

settings = get_settings()
out = Path("seed")
shutil.rmtree(out, ignore_errors=True)
(out / "briefs").mkdir(parents=True)

live = sqlite3.connect(settings.runs_db)
seed = sqlite3.connect(out / "seed.sqlite")
for table in TABLES:
    seed.execute(live.execute("SELECT sql FROM sqlite_master WHERE name = ?", (table,)).fetchone()[0])


def copy(table: str, where: str, args: tuple) -> None:
    for row in live.execute(f"SELECT * FROM {table} WHERE {where}", args):
        seed.execute(f"INSERT INTO {table} VALUES ({','.join('?' * len(row))})", row)


for thread_id in sys.argv[1:]:
    status = live.execute("SELECT status FROM runs WHERE thread_id = ?", (thread_id,)).fetchone()
    assert status and status[0] == "done", f"{thread_id} is not a finished Run"
    last = live.execute("SELECT MAX(checkpoint_id) FROM checkpoints WHERE thread_id = ?", (thread_id,)).fetchone()[0]
    copy("runs", "thread_id = ?", (thread_id,))
    copy("checkpoints", "thread_id = ? AND checkpoint_id = ?", (thread_id, last))
    copy("writes", "thread_id = ? AND checkpoint_id = ?", (thread_id, last))
    shutil.copytree(settings.runs_dir / thread_id, out / "briefs" / thread_id)
seed.commit()
print(f"seeded {len(sys.argv) - 1} Runs, {(out / 'seed.sqlite').stat().st_size // 1024} KB")
