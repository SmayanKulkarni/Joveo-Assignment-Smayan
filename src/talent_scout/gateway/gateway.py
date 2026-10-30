import asyncio
import logging
from datetime import UTC, datetime
from typing import NamedTuple

import httpx
import langsmith as ls

from talent_scout.gateway.adzuna import PAGE_SIZE, AdzunaClient
from talent_scout.gateway.coalesce import coalesce
from talent_scout.gateway.http import TIMEOUT
from talent_scout.gateway.store import POSTINGS, Store, without_closed
from talent_scout.gateway.types import CacheStatus, Fetch, FetchResult, GatewayError, Page, SourceOutcome
from talent_scout.gateway.usajobs import UsajobsClient
from talent_scout.kernel.replay import Replay, open_replay
from talent_scout.kernel.settings import Settings
from talent_scout.kernel.types import Posting, Source


class Served(NamedTuple):
    page: Page
    fetched_at: datetime
    cache: CacheStatus
    failure: str | None = None  # set when L2 answered for a source whose live call failed


class JobsGateway:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self._settings, self._transport = settings, transport
        self._http: httpx.AsyncClient | None = None
        self._store: Store | None = None
        self._replay: Replay | None = None
        self._clients: dict[Source, AdzunaClient | UsajobsClient] = {}
        # One lock per cache key, so concurrent identical Fetches share one call instead of each spending quota.
        self._locks: dict[tuple[Source, str], asyncio.Lock] = {}

    async def __aenter__(self) -> "JobsGateway":
        # Opened here rather than in __init__, so building a gateway touches no files.
        self._store = Store(self._settings)
        try:
            self._http = httpx.AsyncClient(timeout=TIMEOUT, transport=self._transport)
        except BaseException:
            self._store.close()
            raise
        # Opened with the store so a Gateway that is never entered creates no replay file.
        if self._settings.replay_cache:
            self._replay = open_replay(self._settings.replay_cache)
        self._clients = {
            Source.adzuna: AdzunaClient(self._http, self._settings, self._store),
            Source.usajobs: UsajobsClient(self._http, self._settings, self._store),
        }
        return self

    async def __aexit__(self, *exc) -> None:
        try:
            await self._http.aclose()
        finally:
            self._store.close()

    def _replayed(self, source: Source, key: str) -> tuple[Page, datetime] | None:
        row = self._replay.get_jobs(source, key) if self._replay else None
        if row is None:
            return None
        postings, total, dropped, fetched_at = row
        try:
            # No TTL here: a recorded Run must replay the same data however old it is.
            return Page(POSTINGS.validate_json(postings), total, dropped), datetime.fromisoformat(fetched_at)
        except (ValueError, TypeError):  # a row that no longer validates is a miss, and the live answer overwrites it
            return None

    async def _serve(self, source: Source, f: Fetch) -> Served:
        key = f.model_dump_json()
        async with self._locks.setdefault((source, key), asyncio.Lock()):
            if replayed := self._replayed(source, key):
                return Served(*replayed, CacheStatus.replay)
            if cached := self._store.get_l1(source, key):
                served = Served(*cached, CacheStatus.hit)
            else:
                served = await self._beyond_l1(source, f, key)
            page = without_closed(served.page)
            if self._replay:
                self._replay.put_jobs(
                    source, key, POSTINGS.dump_json(page.postings).decode(), page.total, page.dropped, served.fetched_at.isoformat()
                )
            return served._replace(page=page)

    async def _beyond_l1(self, source: Source, f: Fetch, key: str) -> Served:
        # L2 holds Adzuna only: USAJOBS calls are free, and its Postings match poorly.
        stored = self._store.get_l2(f, PAGE_SIZE) if source == Source.adzuna else None
        if stored and len(stored[0].postings) == PAGE_SIZE:  # a short page would skew the Sample, so only a full one skips the call
            return Served(*stored, CacheStatus.store)
        try:
            page = await self._clients[source].search(f)
        except GatewayError as e:  # SourceRejected and bugs are not GatewayErrors, so they still stop the Run
            if stored is None:
                raise
            return Served(*stored, CacheStatus.store, str(e))
        fetched_at = datetime.now(UTC)
        # Stored unfiltered, so the row's expiry still sees every close date.
        self._store.put_l1(source, key, page, fetched_at)
        if source == Source.adzuna:
            self._store.put_l2(f, page.postings, fetched_at)
        return Served(page, fetched_at, CacheStatus.miss)

    async def _resolve(self, source: Source, f: Fetch) -> tuple[list[Posting], SourceOutcome, str | None]:
        # No inputs and only counts as outputs: Postings, URLs and keys never reach LangSmith.
        with ls.trace(f"gateway:{source}", "tool", metadata={"source": source, "page": f.page}) as run:
            page, fetched_at, cache, failure = await self._serve(source, f)
            outcome = SourceOutcome(
                total=page.total, dropped=page.dropped, cache=cache, fetched_at=fetched_at,
                calls_left=self._store.calls_left(source),
            )
            run.add_metadata({"cache": cache, "calls_left": outcome.calls_left})
            run.add_outputs({"count": len(page.postings), "dropped": page.dropped, "total": page.total})
        return page.postings, outcome, failure

    async def fetch(self, f: Fetch) -> FetchResult:
        if not self._clients:
            raise RuntimeError("JobsGateway must be opened with `async with` before fetch")
        # Adzuna always; USAJOBS only covers the US.
        names = [s for s in self._clients if s == Source.adzuna or f.country == "us"]
        answers = await asyncio.gather(*(self._resolve(s, f) for s in names), return_exceptions=True)

        postings, sources, failures = [], {}, {}
        for source, answer in zip(names, answers):
            if isinstance(answer, GatewayError):
                failures[source] = str(answer)
            elif isinstance(answer, BaseException):
                raise answer  # SourceRejected and bugs stop the Run, even if another source answered
            else:
                source_postings, sources[source], failure = answer
                postings += source_postings
                if failure:  # L2 answered for a source whose live call failed, and Collection still needs to know
                    failures[source] = failure
        if not sources:
            raise GatewayError("; ".join(f"{s}: {m}" for s, m in failures.items()))

        kept, merged = coalesce(postings)
        return FetchResult(postings=kept, merged=merged, sources=sources, failures=failures)


def make_gateway(settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> JobsGateway:
    # httpx logs full URLs at INFO, and Adzuna's URL carries app_id and app_key.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return JobsGateway(settings, transport)
