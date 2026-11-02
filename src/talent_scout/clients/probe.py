# Throwaway routes for ticket 05 (Vercel rewrite). Only mounted when PROBE=1; delete this file with that ticket.
import asyncio
import json
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent

COOKIE = dict(key="__Host-probe", value="1", secure=True, httponly=True, samesite="lax", path="/")


def make_router(write_guard) -> APIRouter:
    router = APIRouter(prefix="/api/probe")

    @router.get("/echo")
    async def echo(request: Request) -> JSONResponse:
        # What Render actually received, and whether the cookie came back on a later request.
        response = JSONResponse({
            "host": request.headers.get("host"),
            "origin": request.headers.get("origin"),
            "forwarded": {k: v for k, v in request.headers.items() if k.startswith("x-forwarded") or k.startswith("x-vercel")},
            "cookie_seen": request.cookies.get("__Host-probe"),
        })
        response.set_cookie(**COOKIE)
        return response

    @router.get("/redirect")
    async def redirect() -> RedirectResponse:
        response = RedirectResponse("/api/probe/echo", status_code=302)
        response.set_cookie(**COOKIE)
        return response

    @router.post("/write", dependencies=[Depends(write_guard)])
    async def write() -> dict:
        return {"ok": True}

    @router.get("/stream", response_class=EventSourceResponse)
    async def stream() -> AsyncIterator[ServerSentEvent]:
        # One event a second: buffering shows up as the client getting them all at the end.
        start = time.monotonic()
        for i in range(10):
            yield ServerSentEvent(raw_data=json.dumps({"i": i, "server_s": round(time.monotonic() - start, 2)}))
            await asyncio.sleep(1)

    return router
