import asyncio

import httpx

from talent_scout.gateway.store import Store
from talent_scout.gateway.types import BudgetExhausted, SourceRejected, SourceUnavailable
from talent_scout.kernel.types import Source

TIMEOUT = 10
# Waits before the first and second retry; tests zero them so retries don't sleep.
_DELAYS = (0.5, 1.0)


async def get_json(client: httpx.AsyncClient, source: Source, url: str, store: Store, **kw):
    """GET with retries on timeout, connect error and 5xx. Errors never carry the URL, which holds the keys."""
    for delay in (*_DELAYS, None):
        store.spend(source)  # every attempt counts against the quota, retries included
        try:
            resp = await client.get(url, **kw)
        except httpx.TransportError:  # timeouts, connect errors and dropped connections alike
            pass
        else:
            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError:
                    raise SourceUnavailable(f"{source} returned a body that is not JSON") from None
            if resp.status_code == 429:
                if source != Source.adzuna:  # USAJOBS has no limit to protect, so there is no lockout
                    raise SourceUnavailable(f"{source} is rate limiting") from None
                # No retry: the quota is gone, so refuse everything until the next UTC day.
                store.lock_day(source)
                raise BudgetExhausted(f"{source} daily limit reached")
            if resp.status_code < 500:
                raise SourceRejected(source, resp.status_code, resp.text)
        if delay is None:
            raise SourceUnavailable(f"{source} did not answer after retries") from None
        await asyncio.sleep(delay)
