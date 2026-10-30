import asyncio
import logging
from contextlib import AsyncExitStack
from datetime import UTC, datetime

import httpx

from talent_scout.gateway.adzuna import AdzunaClient
from talent_scout.gateway.coalesce import coalesce
from talent_scout.gateway.http import TIMEOUT
from talent_scout.gateway.types import CacheStatus, Fetch, FetchResult, GatewayError, SourceOutcome
from talent_scout.kernel.settings import Settings
from talent_scout.kernel.types import Source


class JobsGateway:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self._settings, self._transport = settings, transport
        self._stack = AsyncExitStack()
        self._clients: dict[Source, AdzunaClient] = {}

    async def __aenter__(self) -> "JobsGateway":
        http = await self._stack.enter_async_context(httpx.AsyncClient(timeout=TIMEOUT, transport=self._transport))
        self._clients = {Source.adzuna: AdzunaClient(http, self._settings)}
        return self

    async def __aexit__(self, *exc) -> None:
        await self._stack.aclose()

    async def fetch(self, f: Fetch) -> FetchResult:
        names = list(self._clients)
        answers = await asyncio.gather(*(self._clients[s].search(f) for s in names), return_exceptions=True)

        postings, sources, failures = [], {}, {}
        for source, answer in zip(names, answers):
            if isinstance(answer, GatewayError):
                failures[source] = str(answer)
            elif isinstance(answer, BaseException):
                raise answer  # SourceRejected and bugs stop the Run, even if another source answered
            else:
                postings += answer.postings
                sources[source] = SourceOutcome(
                    total=answer.total, dropped=answer.dropped, cache=CacheStatus.miss,
                    fetched_at=datetime.now(UTC), calls_left=None,
                )
        if not sources:
            raise GatewayError("; ".join(f"{s}: {m}" for s, m in failures.items()))

        kept, merged = coalesce(postings)
        return FetchResult(postings=kept, merged=merged, sources=sources, failures=failures)


def make_gateway(settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> JobsGateway:
    # httpx logs full URLs at INFO, and Adzuna's URL carries app_id and app_key.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return JobsGateway(settings, transport)
