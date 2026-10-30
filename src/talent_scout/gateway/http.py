import asyncio

import httpx

from talent_scout.gateway.types import SourceRejected, SourceUnavailable
from talent_scout.kernel.types import Source

TIMEOUT = 10
# Waits before the first and second retry; tests zero them so retries don't sleep.
_DELAYS = (0.5, 1.0)


async def get_json(client: httpx.AsyncClient, source: Source, url: str, **kw):
    """GET with retries on timeout, connect error and 5xx. Errors never carry the URL, which holds the keys."""
    for delay in (*_DELAYS, None):
        try:
            resp = await client.get(url, **kw)
        except (httpx.TimeoutException, httpx.ConnectError):
            pass
        else:
            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError:
                    raise SourceUnavailable(f"{source} returned a body that is not JSON") from None
            if resp.status_code < 500:
                raise SourceRejected(source, resp.status_code, resp.text)
        if delay is None:
            raise SourceUnavailable(f"{source} did not answer after retries") from None
        await asyncio.sleep(delay)
