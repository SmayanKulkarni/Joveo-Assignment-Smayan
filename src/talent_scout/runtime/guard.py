import sqlite3
from pathlib import Path


class RunLocked(Exception):
    def __init__(self, thread_id: str):
        super().__init__(f"Run {thread_id} is open elsewhere")
        self.thread_id = thread_id


def take_lock(runs_db: Path, thread_id: str) -> sqlite3.Connection:
    """Lock a thread across processes. The caller holds the returned connection and closes it to release.

    The OS frees the lock when a process dies. Never commit on the connection, and keep it
    referenced for the whole Run: a commit or garbage collection releases the lock.
    """
    path = runs_db.parent / "locks" / f"{thread_id}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=0, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.Error as e:
        conn.close()
        if e.sqlite_errorname == "SQLITE_BUSY":
            raise RunLocked(thread_id) from e
        raise
    return conn
