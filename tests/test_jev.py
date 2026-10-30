import asyncio
import json

import httpx2
import pytest
from langchain_core.runnables import RunnableLambda
from langchain_typesafe import ClassifierResponse, Noul, NoulAnswer
from langchain_typesafe.client import (
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeAPIResponseValidationError,
    TypeSafeAPITimeoutError,
    TypeSafeBadRequestError,
    TypeSafeInternalServerError,
    TypeSafeNotFoundError,
    TypeSafeRateLimitError,
    TypeSafeUnprocessableEntityError,
)

from talent_scout.kernel import llm
from talent_scout.kernel.jev import MARKER, MAX_STATE_BYTES, Jev, _fit, build_chain, llm_fallback
from talent_scout.kernel.llm import LLMExhausted
from talent_scout.kernel.testing import fake_classifier
from talent_scout.kernel.thresholds import CUTS, UnknownJevModel, cut_for
from test_llm import model, tiers

Q = {"q": Noul(instructions="Is this about software?")}
H = httpx2.Headers()
CUT_MODEL = {"clarity": 0.5, "relevance": 0.5, "critic": 0.5}


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    monkeypatch.setattr(llm, "_BACKOFF", False)


def judge(jev, placement="relevance", state=None, questions=Q):
    return asyncio.run(jev.judge(placement, state or {"t": "x"}, questions))


def api_error(cls, status):
    return cls(status, None, H)


def test_outcome_compares_p_yes_to_cut():
    jev = Jev(fake_classifier({"q": 0.5}), {"typesafe/jev-1.14": {**CUT_MODEL, "relevance": 0.6}})
    j = judge(jev)["q"]
    assert (j.outcome, j.p_yes, j.cut, j.source, j.truncated) == (False, 0.5, 0.6, "jev", False)
    assert judge(Jev(fake_classifier({"q": 0.5}), CUTS))["q"].outcome is True


def test_cut_uses_longest_prefix_of_dated_model_id():
    cuts = {"a/m": {**CUT_MODEL, "critic": 0.1}, "a/m-2026": {**CUT_MODEL, "critic": 0.9}}
    assert cut_for(cuts, "a/m-20260101", "critic") == 0.9
    assert cut_for(cuts, "a/m-20250101", "critic") == 0.1


def test_unknown_model_fails_loudly():
    with pytest.raises(UnknownJevModel):
        judge(Jev(fake_classifier({"q": 1}, model="other/model"), CUTS))


def test_construction_needs_every_placement_cut():
    with pytest.raises(ValueError, match="critic"):
        Jev(fake_classifier({}), {"m": {"clarity": 0.5, "relevance": 0.5}})


def test_oversized_state_truncates_longest_string():
    state = {"short": "ok", "nested": [{"long": "é" * 40_000}]}
    fitted, truncated = _fit(state)
    assert truncated and MARKER in fitted["nested"][0]["long"] and fitted["short"] == "ok"
    assert len(json.dumps(fitted, separators=(",", ":"), ensure_ascii=False).encode()) <= MAX_STATE_BYTES
    assert len(state["nested"][0]["long"]) == 40_000  # caller's state untouched
    jev = Jev(fake_classifier({"q": 1}), CUTS)
    assert judge(jev, state=state)["q"].truncated is True


def test_untruncatable_state_does_not_raise():
    _, truncated = _fit({"k": ["x"] * 20_000})
    assert truncated


def test_concurrent_calls_respect_the_semaphore():
    gauge = {"now": 0, "peak": 0}

    async def slow(request, config=None):
        gauge["now"] += 1
        gauge["peak"] = max(gauge["peak"], gauge["now"])
        await asyncio.sleep(0.01)
        gauge["now"] -= 1
        return await fake_classifier({"q": 1}).ainvoke(request)

    chain = build_chain(RunnableLambda(slow), concurrency=2)

    async def go():
        await asyncio.gather(*[chain.ainvoke({"state": {}, "questions": Q}) for _ in range(6)])

    asyncio.run(go())
    assert gauge["peak"] == 2


RETRIED = [
    api_error(TypeSafeRateLimitError, 429),
    api_error(TypeSafeInternalServerError, 503),
    TypeSafeAPIConnectionError("down"),
    TypeSafeAPITimeoutError(30),
]


@pytest.mark.parametrize("err", RETRIED)
def test_transient_errors_are_retried(err):
    fake = fake_classifier({"q": 1}, errors=[err, err])
    judge(Jev(build_chain(fake, concurrency=2), CUTS))
    assert len(fake.calls) == 3


@pytest.mark.parametrize(
    "err",
    [api_error(TypeSafeBadRequestError, 400), api_error(TypeSafeUnprocessableEntityError, 422)],
)
def test_client_errors_are_not_retried(err):
    fake = fake_classifier({"q": 1}, errors=[err])
    with pytest.raises(type(err)):
        judge(Jev(build_chain(fake, concurrency=2), CUTS))
    assert len(fake.calls) == 1


FALLBACK_GOOD = '{"q": {"answer": true, "reason": "It is."}}'


def with_fallback(jev_errors, *script):
    fake = fake_classifier({"q": 0}, errors=jev_errors)
    cheap = model(*script)
    chain = build_chain(fake, concurrency=2, fallback=llm_fallback(tiers(cheap)))
    return fake, cheap, Jev(chain, CUTS)


@pytest.mark.parametrize(
    "errors",
    [
        RETRIED[:1] * 3,
        [TypeSafeAPIResponseValidationError(200, None, H, "answers")],
        [api_error(TypeSafeNotFoundError, 404)],
    ],
)
def test_fallback_reaches_the_llm(errors):
    _, cheap, jev = with_fallback(errors, FALLBACK_GOOD)
    j = judge(jev)["q"]
    assert (j.source, j.model, j.p_yes, j.outcome, j.reason) == ("llm_fallback", "llm:cheap", 1.0, True, "It is.")
    # The adapter sees the same state and question text.
    sent = cheap.seen[0][-1].content
    assert '"t": "x"' in sent and "Is this about software?" in sent


@pytest.mark.parametrize(
    "err",
    [
        api_error(TypeSafeBadRequestError, 400),
        api_error(TypeSafeUnprocessableEntityError, 422),
        api_error(TypeSafeAPIError, 402),
    ],
)
def test_non_fallback_errors_skip_the_llm(err):
    _, cheap, jev = with_fallback([err], FALLBACK_GOOD)
    with pytest.raises(type(err)):
        judge(jev)
    assert cheap.seen == []


def test_failure_after_the_fallback_propagates_unchanged():
    _, _, jev = with_fallback([api_error(TypeSafeNotFoundError, 404)], "bad", "bad")
    with pytest.raises(LLMExhausted):
        judge(jev)


def test_llm_cheap_has_a_cut():
    assert cut_for(CUTS, "llm:cheap", "clarity") == 0.5
