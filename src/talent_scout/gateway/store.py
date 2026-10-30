import re
import sqlite3
import sys
from datetime import UTC, date, datetime, timedelta

from pydantic import TypeAdapter

from talent_scout.gateway.types import BudgetExhausted, Fetch, Page
from talent_scout.kernel.settings import Settings
from talent_scout.kernel.types import Posting, Source

POSTINGS = TypeAdapter(list[Posting])


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _broad_enough(via: Fetch, f: Fetch) -> bool:
    """Whether the Fetch that last returned a Posting was at least as broad as `f`, so reusing it can't skew the Sample."""
    return (
        _words(via.title) <= _words(f.title)
        and (not via.location or via.location == f.location)
        and via.radius_km >= f.radius_km
        and via.category in (None, f.category)
    )


def _reusable_via(via_json: str, f: Fetch) -> Fetch | None:
    try:
        via = Fetch.model_validate_json(via_json)
    except ValueError:  # a Fetch shape from before a change
        return None
    return via if _broad_enough(via, f) else None


def _fits(p: Posting, via: Fetch, f: Fetch) -> bool:
    """Whether a stored Posting would have come back for `f`, checked the way Adzuna would have."""
    if not _words(f.title) <= _words(p.title) or p.posted_at < today() - timedelta(days=f.max_days_old):
        return False
    if f.category and p.domain != f.category:
        return False
    # A country-wide row says nothing about where the job is, so a located request needs the place in its region.
    return via.location == f.location or not f.location or f.location in (s.lower() for s in p.region)


def today() -> date:
    return datetime.now(UTC).date()


def _today() -> str:
    return today().isoformat()


def without_closed(page: Page) -> Page:
    """Drops Postings past their close date. They are not counted as dropped, which is for mapper failures."""
    now = today()
    return page._replace(postings=[p for p in page.postings if p.closes_at is None or p.closes_at >= now])


class Store:
    """gateway_db: the L1 cache, the L2 Adzuna Postings and the daily budget counters."""

    def __init__(self, settings: Settings):
        settings.gateway_db.parent.mkdir(parents=True, exist_ok=True)
        # Autocommit, so every write is on disk by the time fetch returns and a killed process loses nothing.
        self._db = sqlite3.connect(settings.gateway_db, isolation_level=None, check_same_thread=False)
        self._db.executescript(
            "CREATE TABLE IF NOT EXISTS l1 (source TEXT, fetch TEXT, postings TEXT, total INT, dropped INT,"
            " fetched_at TEXT, expires_at TEXT, PRIMARY KEY (source, fetch));"
            "CREATE TABLE IF NOT EXISTS l2_postings (key TEXT PRIMARY KEY, country TEXT, via TEXT, posting TEXT, last_seen_at TEXT);"
            "CREATE INDEX IF NOT EXISTS l2_last_seen ON l2_postings (last_seen_at);"
            "CREATE TABLE IF NOT EXISTS budget (source TEXT, utc_day TEXT, used INT, PRIMARY KEY (source, utc_day));"
        )
        self._ttl = timedelta(hours=settings.l1_ttl_hours)
        self._fresh = timedelta(days=settings.l2_fresh_days)
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
        self._purge()

    def put_l2(self, f: Fetch, postings: list[Posting], seen_at: datetime) -> None:
        """Upserts one live Adzuna page, so the newest version of each Posting wins and `via` is the Fetch that returned it."""
        rows = [(p.key, f.country, f.model_dump_json(), p.model_dump_json(), seen_at.isoformat()) for p in postings]
        # One transaction: autocommit would sync the disk once per row.
        self._db.execute("BEGIN")
        try:
            self._db.executemany(
                "INSERT INTO l2_postings VALUES (?, ?, ?, ?, ?) ON CONFLICT (key) DO UPDATE SET"
                " country = excluded.country, via = excluded.via, posting = excluded.posting, last_seen_at = excluded.last_seen_at",
                rows,
            )
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
        self._db.execute("COMMIT")
        self._purge()

    def get_l2(self, f: Fetch, size: int) -> tuple[Page, datetime] | None:
        """Page `f.page` of the stored Postings that `f` would have matched, newest first, or None when that slice is empty.

        The slice may be short: the caller decides whether a partial page is good enough. Serving never touches last_seen_at.
        """
        cutoff = self._l2_cutoff()
        # ponytail: full scan of about 8,750 rows (25 calls x 50 x 7 days), add Region and Domain columns if the budget grows
        rows = self._db.execute(
            "SELECT via, posting, last_seen_at FROM l2_postings WHERE country = ? AND last_seen_at >= ?", (f.country, cutoff)
        ).fetchall()
        vias: dict[str, Fetch | None] = {}  # most rows share a `via`, so each is parsed and judged once
        matches = []
        for via_json, posting, seen_at in rows:
            if via_json not in vias:
                vias[via_json] = _reusable_via(via_json, f)
            if (via := vias[via_json]) is None:
                continue
            try:
                p = Posting.model_validate_json(posting)
            except ValueError:  # an old Posting shape; the next live call that returns it rewrites the row
                continue
            if _fits(p, via, f):
                matches.append((p, seen_at))

        matches.sort(key=lambda m: (-m[0].posted_at.toordinal(), m[0].key))  # like sort_by=date
        served = matches[(f.page - 1) * size : f.page * size]
        if not served:
            return None
        return Page([p for p, _ in served], len(matches), 0), datetime.fromisoformat(min(s for _, s in served))

    def _purge(self) -> None:
        """Drops closed L1 rows and stale L2 rows. Runs after each live write, the only moment the tables grow."""
        self._db.execute("DELETE FROM l1 WHERE expires_at < ?", (_today(),))
        self._db.execute("DELETE FROM l2_postings WHERE last_seen_at < ?", (self._l2_cutoff(),))

    def _l2_cutoff(self) -> str:
        """Rows last seen before this are hidden on read and deleted on the next purge."""
        return (datetime.now(UTC) - self._fresh).isoformat()

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
