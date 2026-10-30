import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from talent_scout.runtime.guard import RunLocked, take_lock

# Holds the lock until stdin closes, or exits 3 if refused.
SCRIPT = """
import sys
from pathlib import Path
from talent_scout.runtime.guard import RunLocked, take_lock

try:
    lock = take_lock(Path(sys.argv[1]), "t1")
except RunLocked:
    sys.exit(3)
print("locked", flush=True)
sys.stdin.read()
"""


def lock_process(runs_db: Path) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-c", SCRIPT, str(runs_db)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )


def test_second_process_is_refused_and_the_lock_frees_after_a_kill(tmp_path):
    runs_db = tmp_path / "runs.sqlite"
    holder = lock_process(runs_db)
    try:
        assert holder.stdout.readline().strip() == "locked"

        second = lock_process(runs_db)
        assert second.wait(timeout=30) == 3
        second.stdout.close()
        second.stdin.close()
    finally:
        # A hard kill, as taskkill /F would be: nothing gets to release the lock politely.
        holder.kill()
        holder.wait(timeout=30)
        holder.stdout.close()
        holder.stdin.close()

    take_lock(runs_db, "t1").close()


def test_lock_is_per_thread_and_frees_on_close(tmp_path):
    runs_db = tmp_path / "runs.sqlite"
    first = take_lock(runs_db, "t1")
    with pytest.raises(RunLocked) as refused:
        take_lock(runs_db, "t1")
    assert refused.value.thread_id == "t1"

    take_lock(runs_db, "t2").close()
    first.close()
    take_lock(runs_db, "t1").close()


def test_a_failure_other_than_busy_is_not_reported_as_locked(tmp_path):
    runs_db = tmp_path / "runs.sqlite"
    lock_file = tmp_path / "locks" / "t1.lock"
    lock_file.parent.mkdir()
    lock_file.write_bytes(b"not a database" * 100)

    with pytest.raises(sqlite3.DatabaseError):
        take_lock(runs_db, "t1")
