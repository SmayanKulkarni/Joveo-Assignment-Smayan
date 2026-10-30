import asyncio
import logging
from datetime import UTC, datetime

import httpx

from talent_scout.gateway.adzuna import AdzunaClient
from talent_scout.gateway.coalesce import coalesce
from talent_scout.gateway.http import TIMEOUT
from talent_scout.gateway.store import Store
from talent_scout.gateway.types import CacheStatus, Fetch, FetchResult, GatewayError, SourceOutcome
from talent_scout.kernel.settings import Settings
from talent_scout.kernel.types import Posting, Source


class JobsGateway:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self._settings, self._transport = settings, transport
        self._http: httpx.AsyncClient | None = None
        self._store: Store | None = None
        self._clients: dict[Source, AdzunaClient] = {}

    async def __aenter__(self) -> "JobsGateway":
        # Opened here rather than in __init__, so building a gateway touches no files.
        self._store = Store(self._settings)
        self._http = httpx.AsyncClient(timeout=TIMEOUT, transport=self._transport)
        self._clients = {Source.adzuna: AdzunaClient(self._http, self._settings, self._store)}
        return self

    async def __aexit__(self, *exc) -> None:
        await self._http.aclose()
        self._store.close()

    async def _resolve(self, source: Source, f: Fetch) -> tuple[list[Posting], SourceOutcome]:
        key = f.model_dump_json()
        cached = self._store.get_l1(source, key)
        if cached:
            page, fetched_at = cached
            cache = CacheStatus.hit
        else:
            page = await self._clients[source].search(f)
            fetched_at = datetime.now(UTC)
            self._store.put_l1(source, key, page, fetched_at)
            cache = CacheStatus.miss
        outcome = SourceOutcome(
            total=page.total, dropped=page.dropped, cache=cache, fetched_at=fetched_at,
            calls_left=self._store.calls_left(source),
        )
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
