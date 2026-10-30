import asyncio

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from openrouter.errors import (
    BadRequestResponseError,
    InternalServerResponseError,
    NoResponseError,
    PaymentRequiredResponseError,
    TooManyRequestsResponseError,
    UnauthorizedResponseError,
    UnprocessableEntityResponseError,
)
from pydantic import BaseModel, Field

from talent_scout.kernel import llm
from talent_scout.kernel.llm import LLMExhausted, Tiers, check_balance
from talent_scout.kernel.testing import FakeToolChatModel, make_settings

GOOD = '{"n": 3}'


class Out(BaseModel):
    n: int = Field(description="A count.")


class Scripted(FakeToolChatModel):
    """Replays a script of replies; an Exception item is raised instead of returned."""

    script: list = Field(default_factory=list)
    seen: list = Field(default_factory=list)
    delay: float = 0
    gauge: dict = Field(default_factory=lambda: {"now": 0, "peak": 0})

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        from langchain_core.outputs import ChatGeneration, ChatResult

        self.seen.append(messages)
        self.gauge["now"] += 1
        self.gauge["peak"] = max(self.gauge["peak"], self.gauge["now"])
        try:
            await asyncio.sleep(self.delay)
        finally:
            self.gauge["now"] -= 1
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        msg = item if isinstance(item, AIMessage) else AIMessage(content=item)
        return ChatResult(generations=[ChatGeneration(message=msg)])


def model(*script, **kw):
    return Scripted(messages=iter([]), script=list(script), **kw)


def http_error(cls, status):
    # The SDK constructors need a parsed body; retry rules only look at the class.
    err = cls.__new__(cls)
    err.message, err.status_code = "boom", status
    return err


def tiers(*models, **kw):
    return Tiers({"cheap": list(models), "strong": list(models)}, make_settings(**kw))


def run_structured(t, text="hi"):
    return asyncio.run(t.structured("cheap", Out, system="sys", name="t").ainvoke(text))


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    monkeypatch.setattr(llm, "_BACKOFF", False)


def test_bad_then_good_passes_on_feedback_retry():
    m = model("not json", GOOD)
    assert run_structured(tiers(m)) == Out(n=3)
    retry = m.seen[1]
    assert retry[-2].content == "not json"
    assert "validation error" in retry[-1].content.lower()


def test_two_bad_responses_reach_next_model():
    first, second = model("bad", "worse"), model(GOOD)
    assert run_structured(tiers(first, second)) == Out(n=3)
    assert len(first.seen) == 2


def test_chain_running_out_raises_exhausted():
    t = tiers(model("bad", "bad"), model("bad", "bad"))
    with pytest.raises(LLMExhausted) as e:
        run_structured(t)
    assert (e.value.tier, e.value.name, e.value.attempts) == ("cheap", "t", 4)
    assert e.value.__cause__ is not None


@pytest.mark.parametrize(
    "err",
    [
        http_error(TooManyRequestsResponseError, 429),
        http_error(InternalServerResponseError, 500),
        httpx.ReadTimeout("slow"),
        httpx.ConnectError("down"),
        NoResponseError(),
    ],
)
def test_transient_errors_retry_then_fall_back(err):
    first, second = model(err, err, err), model(GOOD)
    assert run_structured(tiers(first, second)) == Out(n=3)
    assert len(first.seen) == 3


@pytest.mark.parametrize(
    "err",
    [
        http_error(BadRequestResponseError, 400),
        http_error(UnauthorizedResponseError, 401),
        http_error(UnprocessableEntityResponseError, 422),
    ],
)
def test_client_errors_never_fall_back(err):
    first, second = model(err), model(GOOD)
    with pytest.raises(type(err)):
        run_structured(tiers(first, second))
    assert second.seen == []


def test_402_retries_but_never_falls_back():
    err = http_error(PaymentRequiredResponseError, 402)
    first, second = model(err, err, err), model(GOOD)
    with pytest.raises(PaymentRequiredResponseError):
        run_structured(tiers(first, second))
    assert len(first.seen) == 3 and second.seen == []


def test_concurrent_calls_respect_the_semaphore():
    m = model(*[GOOD] * 6, delay=0.01)
    t = tiers(m, llm_concurrency=2)
    run = t.structured("cheap", Out, system="sys", name="t")

    async def go():
        return await asyncio.gather(*[run.ainvoke("x") for _ in range(6)])

    asyncio.run(go())
    assert m.gauge["peak"] == 2


def test_run_is_named_and_models_tagged():
    from langchain_core.tracers.context import collect_runs

    m = model(GOOD)
    run = tiers(m).structured("cheap", Out, system="sys", name="intake")

    async def go():
        with collect_runs() as cb:
            await run.ainvoke("x")
        return cb.traced_runs[0]

    root = asyncio.run(go())
    assert root.name == "llm:intake"
    assert root.metadata["tier"] == "cheap" and root.metadata["name"] == "intake"
    child_tags = {t for r in _walk(root) for t in r.tags or []}
    assert {"tier:cheap", "model:Scripted"} <= child_tags


def _walk(run):
    yield run
    for c in run.child_runs:
        yield from _walk(c)


@tool
def ping(x: int) -> int:
    """Return x."""
    return x


CALL = AIMessage(content="", tool_calls=[{"name": "ping", "args": {"x": 1}, "id": "1"}])


def run_chat(t):
    return asyncio.run(t.chat("cheap", tools=[ping], name="fetch").ainvoke([HumanMessage("go")]))


def test_chat_returns_tool_calls():
    out = run_chat(tiers(model(CALL)))
    assert out.tool_calls[0]["name"] == "ping"


def test_chat_fallback_keeps_tools_bound():
    first, second = model(http_error(InternalServerResponseError, 500)), model(CALL)
    first.script *= 3
    out = run_chat(tiers(first, second))
    assert out.tool_calls and second.bound_tools == [ping]


def test_check_balance(monkeypatch):
    def fake_get(url, **kw):
        assert url.endswith("/api/v1/key")
        return httpx.Response(200, json={"data": {"effective_budget": {"remaining_usd": FAKE["left"]}}}, request=httpx.Request("GET", url))

    class FakeClient:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, url, **kw): return fake_get(url, **kw)

    monkeypatch.setattr(llm.httpx, "AsyncClient", FakeClient)
    s = make_settings(balance_floor_usd=0.25)
    FAKE = {"left": 0.1}
    with pytest.raises(llm.BalanceTooLow):
        asyncio.run(check_balance(s))
    FAKE["left"] = 1.5
    assert asyncio.run(check_balance(s)) == 1.5
