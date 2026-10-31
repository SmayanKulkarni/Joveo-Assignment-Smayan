import asyncio
from types import SimpleNamespace

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import START, MessagesState, StateGraph
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


def cut_off(content):
    return AIMessage(content=content, response_metadata={"finish_reason": "length"})


def test_a_cut_off_reply_skips_the_feedback_retry_and_reaches_the_next_model():
    first, second = model(cut_off('{"n":')), model(GOOD)
    assert run_structured(tiers(first, second)) == Out(n=3)
    assert len(first.seen) == 1


def test_a_cut_off_reply_counts_real_attempts_and_is_bad_output():
    with pytest.raises(LLMExhausted) as e:
        run_structured(tiers(model("bad", cut_off('{"n":'))))
    assert e.value.attempts == 2 and e.value.bad_output
    with pytest.raises(LLMExhausted) as e:
        run_structured(tiers(model(cut_off('{"n":'))))
    assert e.value.attempts == 1 and e.value.bad_output


def test_a_cut_off_reply_that_still_validates_is_kept():
    m = model(cut_off(GOOD))
    assert run_structured(tiers(m)) == Out(n=3)
    assert len(m.seen) == 1


def test_chain_running_out_raises_exhausted():
    t = tiers(model("bad", "bad"), model("bad", "bad"))
    with pytest.raises(LLMExhausted) as e:
        run_structured(t)
    assert (e.value.tier, e.value.name, e.value.attempts) == ("cheap", "t", 4)
    assert e.value.__cause__ is not None
    assert e.value.bad_output


def test_bad_output_follows_the_last_failure_in_the_chain():
    down = [httpx.ConnectError("down")] * 3
    bad = ["bad", "bad"]
    for scripts, expected in (
        ((down, down), False),
        ((bad, bad), True),
        ((bad, down), False),
        ((down, bad), True),
    ):
        with pytest.raises(LLMExhausted) as e:
            run_structured(tiers(*(model(*s) for s in scripts)))
        assert e.value.bad_output is expected


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


class FakeFrame:
    def __init__(self, data):
        self.data = data

    def model_dump(self, **kw):
        return self.data


def delta(text, finish=None, **top):
    choice = {"index": 0, "delta": {"role": "assistant", "content": text}, "finish_reason": finish}
    return FakeFrame({"id": "g", "model": "m", "choices": [choice], **top})


USAGE = FakeFrame(
    {"id": "g", "model": "m", "choices": [], "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7, "cost": 0.0123}}
)
TOP_ERROR = FakeFrame({"id": "g", "choices": [], "error": {"code": 502, "message": "upstream died"}})
MID_ERROR = delta("", finish="error", error={"code": 502, "message": "upstream died"})


def streaming_model(*scripts):
    """The real _CostedOpenRouter on a fake SDK client, since the bugs live on its streaming path."""
    m = llm._CostedOpenRouter(model="fake/m", api_key="x", max_retries=0)
    calls = {"n": 0}
    remaining = list(scripts)

    async def send_async(messages, **params):
        calls["n"] += 1
        frames = remaining.pop(0)

        async def stream():
            for f in frames:
                yield f

        return stream()

    object.__setattr__(m, "client", SimpleNamespace(chat=SimpleNamespace(send_async=send_async)))
    return m, calls


def run_streamed(t):
    # Only "messages" mode sends ainvoke down _astream, so a plain ainvoke wouldn't test this path.
    seen = {}

    async def node(state):
        seen["reply"] = await t.chat("cheap", tools=[], name="fetch").ainvoke([HumanMessage("go")])
        return {}

    g = StateGraph(MessagesState)
    g.add_node("n", node)
    g.add_edge(START, "n")

    async def drive():
        chunks = [c async for c in g.compile().astream({"messages": []}, stream_mode="messages")]
        return chunks

    seen["chunks"] = asyncio.run(drive())
    return seen


STREAM_OK = [delta("he"), delta("llo", finish="stop"), USAGE]


@pytest.mark.parametrize("bad", [[delta("par"), MID_ERROR], [TOP_ERROR], []])
def test_stream_failure_retries_instead_of_returning_it(bad):
    m, calls = streaming_model(bad, STREAM_OK)
    out = run_streamed(tiers(m))
    assert out["reply"].text == "hello" and calls["n"] == 2


@pytest.mark.parametrize("bad", [[delta("par"), MID_ERROR], [TOP_ERROR], []])
def test_stream_failure_falls_back_then_exhausts(bad):
    first, first_calls = streaming_model(bad, bad, bad)
    second, _ = streaming_model(STREAM_OK)
    assert run_streamed(tiers(first, second))["reply"].text == "hello"
    assert first_calls["n"] == 3

    only, _ = streaming_model(bad, bad, bad)
    with pytest.raises(LLMExhausted):
        run_streamed(tiers(only))


def test_stream_keeps_tokens_and_cost():
    m, _ = streaming_model(STREAM_OK)
    out = run_streamed(tiers(m))
    assert "".join(c.text for c, _ in out["chunks"]) == "hello"
    assert out["reply"].usage_metadata["total_cost"] == 0.0123


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
