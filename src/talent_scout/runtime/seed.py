import shutil
import sqlite3

from talent_scout.kernel.settings import Settings

# Written by scripts/export_seed.py; the columns must match the live tables.
TABLES = ("checkpoints", "writes", "runs")


def seed_runs(settings: Settings) -> None:
    """Copy the sample Runs in seed_dir into this install, skipping any whose id is already there."""
    src = settings.seed_dir
    if src is None or not (src / "seed.sqlite").is_file():
        return
    with sqlite3.connect(settings.runs_db, timeout=30) as db:
        db.execute("ATTACH ? AS seed", (str(src / "seed.sqlite"),))
        new = [r[0] for r in db.execute("SELECT thread_id FROM seed.runs WHERE thread_id NOT IN (SELECT thread_id FROM main.runs)")]
        marks = ",".join("?" * len(new))
        for table in TABLES if new else ():
            db.execute(f"INSERT OR IGNORE INTO main.{table} SELECT * FROM seed.{table} WHERE thread_id IN ({marks})", new)
    for thread_id in new:
        if (briefs := src / "briefs" / thread_id).is_dir():
            shutil.copytree(briefs, settings.runs_dir / thread_id, dirs_exist_ok=True)
