import sqlite3
import sys
from datetime import UTC, datetime, timedelta

from pydantic import TypeAdapter

from talent_scout.gateway.types import BudgetExhausted, Page
from talent_scout.kernel.settings import Settings
from talent_scout.kernel.types import Posting, Source

POSTINGS = TypeAdapter(list[Posting])


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


class Store:
    """gateway_db: the L1 cache and the daily budget counters."""

    def __init__(self, settings: Settings):
        settings.gateway_db.parent.mkdir(parents=True, exist_ok=True)
        # Autocommit, so every write is on disk by the time fetch returns and a killed process loses nothing.
        self._db = sqlite3.connect(settings.gateway_db, isolation_level=None, check_same_thread=False)
        self._db.executescript(
            "CREATE TABLE IF NOT EXISTS l1 (source TEXT, fetch TEXT, postings TEXT, total INT, dropped INT,"
            " fetched_at TEXT, expires_at TEXT, PRIMARY KEY (source, fetch));"
            "CREATE TABLE IF NOT EXISTS budget (source TEXT, utc_day TEXT, used INT, PRIMARY KEY (source, utc_day));"
        )
        self._ttl = timedelta(hours=settings.l1_ttl_hours)
        # Only Adzuna has a quota to protect; USAJOBS is counted but unmetered.
        self._limits = {Source.adzuna: settings.adzuna_daily_limit}

    def close(self) -> None:
        self._db.close()

    def get_l1(self, source: Source, fetch_json: str) -> tuple[Page, datetime] | None:
        row = self._db.execute(
            "SELECT postings, total, dropped, fetched_at FROM l1 WHERE source = ? AND fetch = ?", (source, fetch_json)
        ).fetchone()
        if row is None:
            return None
        postings, total, dropped, fetched_at = row
        try:
            fetched_at = datetime.fromisoformat(fetched_at)
            # A fetched_at in the future (clock moved back) counts as stale too, or it would never expire.
            if not timedelta(0) <= datetime.now(UTC) - fetched_at < self._ttl:
                return None
            return Page(POSTINGS.validate_json(postings), total, dropped), fetched_at
        except (ValueError, TypeError):  # a corrupt row or an old Posting shape (pydantic's error is a ValueError); the live call overwrites it
            return None

    def put_l1(self, source: Source, fetch_json: str, page: Page, fetched_at: datetime) -> None:
        closes = [p.closes_at for p in page.postings]
        # One open-ended Posting (or none at all) keeps the row alive, so it is only ever overwritten.
        expires_at = max(closes).isoformat() if closes and None not in closes else None
        self._db.execute(
            "INSERT OR REPLACE INTO l1 VALUES (?, ?, ?, ?, ?, ?, ?)",
            (source, fetch_json, POSTINGS.dump_json(page.postings).decode(), page.total, page.dropped,
             fetched_at.isoformat(), expires_at),
        )

    def spend(self, source: Source) -> None:
        """Counts one HTTP attempt, or raises BudgetExhausted when today's limit is already used."""
        day = _today()
        self._db.execute("INSERT OR IGNORE INTO budget VALUES (?, ?, 0)", (source, day))
        # One statement, so the check and the increment can't be split by another caller.
        spent = self._db.execute(
            "UPDATE budget SET used = used + 1 WHERE source = ? AND utc_day = ? AND used < ? RETURNING used",
            (source, day, self._limits.get(source, sys.maxsize)),
        ).fetchall()
        if not spent:
            raise BudgetExhausted(f"{source} daily limit reached")

    def lock_day(self, source: Source) -> None:
        """Marks today's budget as spent, after the API itself said the quota is gone."""
        if source not in self._limits:  # unmetered, so there is nothing to lock
            return
        self._db.execute(
            "INSERT INTO budget VALUES (?, ?, ?) ON CONFLICT (source, utc_day) DO UPDATE SET used = MAX(used, excluded.used)",
            (source, _today(), self._limits[source]),
        )

    def calls_left(self, source: Source) -> int | None:
        limit = self._limits.get(source)
        if limit is None:
            return None
        row = self._db.execute("SELECT used FROM budget WHERE source = ? AND utc_day = ?", (source, _today())).fetchone()
        return max(limit - (row[0] if row else 0), 0)
