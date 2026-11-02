"""Pack finished local Runs, and the Customers they belong to, into seed/ so a fresh deploy starts with them.

Usage: uv run python scripts/export_seed.py [THREAD_ID ...]   (no ids: every finished Run)
Only each Run's last checkpoint is kept: that is all the Brief and the log need.
Resumes stay behind, because seed/ is committed to a public repo.
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
        seed.execute(f"INSERT OR IGNORE INTO {table} VALUES ({','.join('?' * len(row))})", row)


ids = sys.argv[1:] or [r[0] for r in live.execute("SELECT thread_id FROM runs WHERE status = 'done' ORDER BY created_at")]
for thread_id in ids:
    status, customer_id = live.execute("SELECT status, customer_id FROM runs WHERE thread_id = ?", (thread_id,)).fetchone()
    assert status == "done", f"{thread_id} is not a finished Run"
    last = live.execute(
        "SELECT MAX(checkpoint_id) FROM checkpoints WHERE thread_id = ? AND checkpoint_ns = ''", (thread_id,)
    ).fetchone()[0]
    copy("runs", "thread_id = ?", (thread_id,))
    copy("checkpoints", "thread_id = ? AND checkpoint_ns = '' AND checkpoint_id = ?", (thread_id, last))
    copy("writes", "thread_id = ? AND checkpoint_ns = '' AND checkpoint_id = ?", (thread_id, last))
    copy("customers", "id = ?", (customer_id,))
    copy("customer_profiles", "customer_id = ?", (customer_id,))
    shutil.copytree(settings.runs_dir / thread_id, out / "briefs" / thread_id)
# A deploy without sign-in runs as the local CSM, so the Customers show up there as they do here.
seed.execute("UPDATE customers SET csm_id = 'local'")
seed.commit()
print(f"seeded {len(ids)} Runs, {(out / 'seed.sqlite').stat().st_size // 1024} KB")