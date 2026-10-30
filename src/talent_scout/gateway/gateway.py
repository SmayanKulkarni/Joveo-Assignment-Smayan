import asyncio
import logging
from datetime import UTC, datetime

import httpx
import langsmith as ls

from talent_scout.gateway.adzuna import AdzunaClient
from talent_scout.gateway.coalesce import coalesce
from talent_scout.gateway.http import TIMEOUT
from talent_scout.gateway.store import POSTINGS, Store
from talent_scout.gateway.types import CacheStatus, Fetch, FetchResult, GatewayError, Page, SourceOutcome
from talent_scout.kernel.replay import Replay, open_replay
from talent_scout.kernel.settings import Settings
from talent_scout.kernel.types import Posting, Source


class JobsGateway:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self._settings, self._transport = settings, transport
        self._http: httpx.AsyncClient | None = None
        self._store: Store | None = None
        self._replay: Replay | None = None
        self._clients: dict[Source, AdzunaClient] = {}
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
        self._clients = {Source.adzuna: AdzunaClient(self._http, self._settings, self._store)}
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

    async def _serve(self, source: Source, f: Fetch) -> tuple[Page, datetime, CacheStatus]:
        key = f.model_dump_json()
        async with self._locks.setdefault((source, key), asyncio.Lock()):
            if replayed := self._replayed(source, key):
                return *replayed, CacheStatus.replay
            cached = self._store.get_l1(source, key)
            if cached:
                (page, fetched_at), cache = cached, CacheStatus.hit
            else:
                page = await self._clients[source].search(f)
                fetched_at, cache = datetime.now(UTC), CacheStatus.miss
                self._store.put_l1(source, key, page, fetched_at)
            if self._replay:
                self._replay.put_jobs(
                    source, key, POSTINGS.dump_json(page.postings).decode(), page.total, page.dropped, fetched_at.isoformat()
                )
            return page, fetched_at, cache

    async def _resolve(self, source: Source, f: Fetch) -> tuple[list[Posting], SourceOutcome]:
        # No inputs and only counts as outputs: Postings, URLs and keys never reach LangSmith.
        with ls.trace(f"gateway:{source}", "tool", metadata={"source": source, "page": f.page}) as run:
            page, fetched_at, cache = await self._serve(source, f)
            outcome = SourceOutcome(
                total=page.total, dropped=page.dropped, cache=cache, fetched_at=fetched_at,
                calls_left=self._store.calls_left(source),
            )
            run.add_metadata({"cache": cache, "calls_left": outcome.calls_left})
            run.add_outputs({"count": len(page.postings), "dropped": page.dropped, "total": page.total})
        return page.postings, outcome

    async def fetch(self, f: Fetch) -> FetchResult:
        if not self._clients:
            raise RuntimeError("JobsGateway must be opened with `async with` before fetch")
        names = list(self._clients)
        answers = await asyncio.gather(*(self._resolve(s, f) for s in names), return_exceptions=True)

        postings, sources, failures = [], {}, {}
        for source, answer in zip(names, answers):
            if isinstance(answer, GatewayError):
                failures[source] = str(answer)
            elif isinstance(answer, BaseException):
                raise answer  # SourceRejected and bugs stop the Run, even if another source answered
            else:
                source_postings, sources[source] = answer
                postings += source_postings
        if not sources:
            raise GatewayError("; ".join(f"{s}: {m}" for s, m in failures.items()))

        kept, merged = coalesce(postings)
        return FetchResult(postings=kept, merged=merged, sources=sources, failures=failures)


def make_gateway(settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> JobsGateway:
    # httpx logs full URLs at INFO, and Adzuna's URL carries app_id and app_key.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return JobsGateway(settings, transport)
