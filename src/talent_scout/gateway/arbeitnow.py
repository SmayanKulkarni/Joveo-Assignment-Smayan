import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx

from talent_scout.gateway import store as clock
from talent_scout.gateway.adzuna import collapse
from talent_scout.gateway.http import get_json
from talent_scout.gateway.store import Store
from talent_scout.gateway.types import Fetch, GatewayError, Page, SourceRejected, SourceUnavailable
from talent_scout.kernel.types import Posting, Source

log = logging.getLogger(__name__)

URL = "https://www.arbeitnow.com/api/job-board-api"
PAGE_SIZE = 50
MAX_PAGES = 40  # the feed ends near page 21, so this only stops a feed that never returns an empty page
MAX_DESCRIPTION = 4000
# Cloudflare answers 429 to pages fetched back to back, so the walk spaces them; tests zero it.
PAGE_PAUSE = 2.5
SNAPSHOT = "snapshot"
REMOTE = ("Remote",)

# The feed merges five country sites; the job URL's host says which one a Posting came from.
HOST_COUNTRY = {"arbeitnow.com": "de", "arbeitnow.co.uk": "gb", "arbeitnow.fr": "fr", "arbeitnow.ch": "ch", "arbeitnow.nl": "nl"}
# Adzuna's name for each country at the root of its area list, so the places chart groups mixed Samples by city.
ADZUNA_ROOT = {"de": "Deutschland", "gb": "UK", "fr": "France", "ch": "Schweiz", "nl": "Nederland"}

# Held across Runs, so two Runs never walk the feed at once.
_WALK = asyncio.Lock()


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _strip(html: str) -> str:
    parser = _Text()
    parser.feed(html)
    return collapse(" ".join(parser.parts))


def _country(url: str) -> str:
    return HOST_COUNTRY[(urlsplit(url).hostname or "").removeprefix("www.")]


def _city(location: str) -> str:
    return location.split(",")[0].strip()


def _is_remote(raw: dict, location: str) -> bool:
    # The flag, the location and the tags disagree often, so any one of them is enough.
    return bool(raw.get("remote")) or "remote" in location.lower() or any(str(t).lower() == "remote" for t in raw.get("tags") or [])


def _map(raw: dict) -> Posting:
    country = _country(raw["url"])
    location = collapse(raw.get("location") or "")
    remote = _is_remote(raw, location)
    city = "" if remote else _city(location)
    description = _strip(raw["description"])[:MAX_DESCRIPTION]
    # An empty description is a prefix of every other, so coalesce would merge it with any Posting of the same job title.
    if not description:
        raise ValueError("blank description")
    return Posting(
        source=Source.arbeitnow,
        source_id=raw["slug"],
        title=collapse(raw["title"]),
        company=collapse(raw.get("company_name") or "") or None,
        location=location or ADZUNA_ROOT[country],
        region=REMOTE if remote else (ADZUNA_ROOT[country], city) if city else (ADZUNA_ROOT[country],),
        domain=None,
        posted_at=datetime.fromtimestamp(raw["created_at"], UTC).date(),
        closes_at=None,
        description=description,
        url=raw["url"],
        salary=None,
        remote=remote,
    )


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _matches(p: Posting, f: Fetch) -> bool:
    if not _words(f.title) <= _words(p.title) or p.posted_at < clock.today() - timedelta(days=f.max_days_old):
        return False
    # A remote Posting can be taken from anywhere, so the place filters leave it alone.
    if p.remote:
        return True
    # ponytail: exact city match, so "munich" misses "München"; add an alias table if that costs real Runs.
    return _country(p.url) == f.country and (not f.location or " ".join(_city(p.location).lower().split()) == f.location)


class ArbeitnowClient:
    def __init__(self, client: httpx.AsyncClient, store: Store):
        self._client, self._store = client, store
        self._failure: str | None = None  # a failed walk is not retried for the rest of this Run

    async def _walk(self) -> Page:
        postings: dict[str, Posting] = {}
        dropped = 0
        for page in range(1, MAX_PAGES + 1):
            if page > 1:
                await asyncio.sleep(PAGE_PAUSE)
            try:
                body = await get_json(self._client, Source.arbeitnow, URL, self._store, params={"page": page})
            except SourceRejected as e:  # the feed needs no key, so a refusal is the source failing, not a bug of ours
                raise SourceUnavailable(f"arbeitnow refused the request with {e.status}") from None
            data = body.get("data") if isinstance(body, dict) else None
            if not isinstance(data, list):
                raise SourceUnavailable("arbeitnow returned a body without data") from None
            if not data:
                break
            for raw in data:
                try:
                    p = _map(raw)
                except (KeyError, TypeError, ValueError):  # ValueError covers pydantic's ValidationError
                    dropped += 1
                    log.warning("dropped arbeitnow result %s", raw.get("slug") if isinstance(raw, dict) else None)
                else:
                    postings.setdefault(p.key, p)  # pages shift by an item between cached copies, so a Posting can repeat
        return Page(list(postings.values()), len(postings), dropped)

    async def _snapshot(self) -> Page:
        async with _WALK:
            # Checked once the lock is held, because the Run ahead of this one may just have walked.
            if cached := self._store.get_l1(Source.arbeitnow, SNAPSHOT):
                return cached[0]
            if self._failure:
                raise SourceUnavailable(self._failure)
            try:
                snapshot = await self._walk()
            except GatewayError as e:  # the partial walk goes out of scope here, so a half snapshot is never stored
                self._failure = str(e)
                raise
            self._store.put_l1(Source.arbeitnow, SNAPSHOT, snapshot, datetime.now(UTC))
            return snapshot

    async def search(self, f: Fetch) -> Page:
        snapshot = await self._snapshot()
        found = sorted((p for p in snapshot.postings if _matches(p, f)), key=lambda p: (-p.posted_at.toordinal(), p.key))
        served = found[(f.page - 1) * PAGE_SIZE : f.page * PAGE_SIZE]
        return Page(served, len(found), snapshot.dropped if f.page == 1 else 0)
