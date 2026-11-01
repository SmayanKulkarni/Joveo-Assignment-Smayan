from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from talent_scout.brief.glance import Glance, glance
from talent_scout.brief.markdown import CONFIDENCE_KEY
from talent_scout.brief.types import MarketBrief
from talent_scout.kernel.llm import BalanceTooLow
from talent_scout.kernel.settings import Settings
from talent_scout.kernel.state import LogKind
from talent_scout.kernel.types import ADZUNA_CATEGORIES, ADZUNA_CURRENCY, Dimension, Model, NonBlank
from talent_scout.runtime.controller import InvalidAnswer, NotResumable, RunController, RunHandle, RunView, UnknownRun
from talent_scout.runtime.events import Stopped
from talent_scout.runtime.graph import graph_topology
from talent_scout.runtime.guard import RunLocked
from talent_scout.runtime.pause import Pause
from talent_scout.runtime.registry import RunRecord

DIST = Path(__file__).resolve().parents[3] / "web" / "dist"
LOOPBACK_HOSTS = ["127.0.0.1", "localhost"]
# The one synthetic message: it ends the replay, and isn't a RunEvent.
CAUGHT_UP = ServerSentEvent(raw_data='{"type": "caught_up"}')

# Each refusal's status and code, found by isinstance so a subclass is covered too.
REFUSALS = {
    UnknownRun: (404, "unknown_run"),
    RunLocked: (409, "run_locked"),
    NotResumable: (409, "not_resumable"),
    BalanceTooLow: (402, "balance_too_low"),
    httpx.HTTPError: (502, "upstream"),  # from check_balance
}


class Refusal(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code = status, code


class StartRequest(Model):
    request_text: NonBlank
    focus: list[Dimension] = []


class Started(Model):
    thread_id: str


class ResumeRequest(Model):
    answer: dict | None = None


class LogLine(Model):
    node: str
    kind: LogKind
    message: str


class PostingRef(Model):
    key: str
    title: str
    company: str | None
    location: str
    url: str | None
    posted_at: date


class RunDetail(Model):
    # Not RunView: its state holds LangChain messages and every Posting's full text.
    record: RunRecord
    request_text: str | None  # None before the first checkpoint
    focus: list[Dimension]
    pause: Pause | None
    stopped_at: str | None
    run_log: list[LogLine]
    live_from: int | None  # the attached handle's log_start; None when no Run is live here
    brief: MarketBrief | None
    sample: list[PostingRef]  # empty unless there is a Brief
    glance: Glance | None  # computed on read, so earlier Runs get it and brief.json keeps its bytes


def _http_url(url: str) -> str | None:
    # Only http(s), the same guard as the Markdown links: anything else would be a live link on screen.
    return url if urlparse(url).scheme in ("http", "https") else None


def _detail(view: RunView, handle: RunHandle | None) -> RunDetail:
    state = view.state
    sample = []
    if state and state.brief:
        sample = [
            PostingRef(
                key=p.key, title=p.title, company=p.company, location=p.location, url=_http_url(p.url), posted_at=p.posted_at
            )
            for p in state.sample_postings
        ]
    return RunDetail(
        record=view.record,
        request_text=state.request_text if state else None,
        focus=state.focus if state else [],
        pause=view.pause,
        stopped_at=view.stopped_at,
        run_log=[LogLine(node=e.node, kind=e.kind, message=e.message) for e in state.run_log] if state else [],
        live_from=handle.log_start if handle else None,
        brief=state.brief if state else None,
        sample=sample,
        glance=glance(state.brief, state.sample_postings) if state and state.brief else None,
    )


def _clean(errors: list[dict]) -> list[dict]:
    # A field error has loc ["plan", "radius_km"], and a model-level one has [].
    return [{"loc": list(e.get("loc", [])), "msg": e["msg"].removeprefix("Value error, ")} for e in errors]


def _controller(request: Request) -> RunController:
    return request.app.state.controller


async def same_origin(request: Request) -> None:
    # A page on another origin can still send a POST to localhost, and a body-less cancel would pass a content-type check.
    origin = request.headers.get("origin")
    if origin and origin.partition("://")[2] != request.headers["host"]:
        raise Refusal(403, "foreign_origin", "This request came from another origin")


async def live_handle(thread_id: str, request: Request) -> RunHandle:
    controller = _controller(request)
    await controller.get_pause(thread_id)  # an unknown Run becomes a 404
    handle = controller.attached(thread_id)
    if handle is None:
        raise HTTPException(204)  # EventSource's stop signal: the stream closes and doesn't retry
    return handle


api = APIRouter(prefix="/api")


@api.get("/meta")
async def meta(request: Request) -> dict:
    return {
        "graph": graph_topology(),
        "dimensions": [d.value for d in Dimension],
        "countries": sorted(ADZUNA_CURRENCY),
        "categories": sorted(ADZUNA_CATEGORIES),
        "confidence_key": CONFIDENCE_KEY,
        "demo": request.app.state.settings.demo,
    }


@api.get("/runs")
async def list_runs(request: Request) -> list[RunRecord]:
    return await _controller(request).list_runs()


@api.post("/runs", status_code=201, dependencies=[Depends(same_origin)])
async def start_run(body: StartRequest, request: Request) -> Started:
    handle = await _controller(request).start(body.request_text, body.focus)
    return Started(thread_id=handle.thread_id)


@api.get("/runs/{thread_id}")
async def get_run(thread_id: str, request: Request) -> RunDetail:
    controller = _controller(request)
    view = await controller.get_run(thread_id)
    # No await between the read and this lookup, so live_from names the handle that is current.
    return _detail(view, controller.attached(thread_id))


@api.post("/runs/{thread_id}/resume", dependencies=[Depends(same_origin)])
async def resume_run(thread_id: str, body: ResumeRequest, request: Request) -> Started:
    handle = await _controller(request).resume(thread_id, body.answer)
    return Started(thread_id=handle.thread_id)


@api.post("/runs/{thread_id}/cancel", dependencies=[Depends(same_origin)])
async def cancel_run(thread_id: str, request: Request) -> Stopped:
    controller = _controller(request)
    await controller.get_pause(thread_id)  # an unknown Run becomes a 404
    handle = controller.attached(thread_id)
    if handle is None:
        raise Refusal(409, "not_live", "This Run isn't running here")
    return await handle.cancel()


@api.get("/runs/{thread_id}/brief.{kind}")
async def download_brief(thread_id: str, kind: Literal["json", "md"], request: Request) -> FileResponse:
    controller = _controller(request)
    await controller.get_pause(thread_id)  # an unknown Run becomes a 404
    path = controller.brief_paths(thread_id)[kind == "md"]
    if not path.is_file():
        raise Refusal(404, "no_brief", "This Run has no Brief")
    return FileResponse(path, filename=f"brief-{thread_id}.{kind}")


@api.get("/runs/{thread_id}/events", response_class=EventSourceResponse)
async def events(handle: Annotated[RunHandle, Depends(live_handle)]) -> AsyncIterator[ServerSentEvent]:
    replay = handle.buffered  # nothing awaits before events() takes its snapshot, so the count is exact
    if replay == 0:
        yield CAUGHT_UP
    sent = 0
    # Never wrapped in a timeout: that would kill the generator, and a disconnect needs no code here.
    async for event in handle.events():
        yield ServerSentEvent(raw_data=event.model_dump_json())
        sent += 1
        if sent == replay:
            yield CAUGHT_UP


def make_app(settings: Settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with RunController.open(settings) as controller:
            app.state.controller = controller
            yield

    app = FastAPI(lifespan=lifespan)
    app.state.settings = settings
    # Stops DNS rebinding. Plain ASGI middleware, so nothing sits between a stream and its disconnect handling.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=LOOPBACK_HOSTS)

    def refuse(status: int, code: str, message: str, **extra) -> JSONResponse:
        return JSONResponse({"code": code, "message": message, **extra}, status_code=status)

    @app.exception_handler(Refusal)
    async def _refusal(request: Request, exc: Refusal):
        return refuse(exc.status, exc.code, str(exc))

    for error, (status, code) in REFUSALS.items():
        app.add_exception_handler(error, lambda request, exc, s=status, c=code: refuse(s, c, str(exc) or c))

    @app.exception_handler(InvalidAnswer)
    async def _invalid_answer(request: Request, exc: InvalidAnswer):
        # Pydantic's raw errors hold exception objects in ctx, which JSON can't carry.
        return refuse(422, "invalid_answer", "The answer was not valid", errors=_clean(exc.errors))

    @app.exception_handler(RequestValidationError)
    async def _invalid(request: Request, exc: RequestValidationError):
        return refuse(422, "invalid_request", "The request was not valid", errors=_clean(exc.errors()))

    app.include_router(api)
    if (DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=DIST / "assets"))

    @app.get("/{path:path}", include_in_schema=False)
    async def single_page(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404)  # a real 404, not the app shell
        if not (DIST / "index.html").is_file():
            return PlainTextResponse("The web app isn't built. Run: npm --prefix web run build", status_code=503)
        return FileResponse(DIST / "index.html")  # every client route, so /runs/:id survives a reload

    return app
