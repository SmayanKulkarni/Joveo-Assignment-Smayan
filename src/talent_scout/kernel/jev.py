import asyncio
import json
from typing import Literal

from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from langchain_typesafe import ClassifierResponse, Noul, NoulAnswer, TypeSafeClassifier
from langchain_typesafe.client import (
    TypeSafeAPIConnectionError,
    TypeSafeAPIResponseValidationError,
    TypeSafeInternalServerError,
    TypeSafeNotFoundError,
    TypeSafeRateLimitError,
)
from pydantic import Field, create_model

from talent_scout.kernel import llm
from talent_scout.kernel.llm import Tiers, make_tiers
from talent_scout.kernel.replay import Replay, open_replay
from talent_scout.kernel.settings import Settings
from talent_scout.kernel.thresholds import CUTS, PLACEMENTS, Placement, cut_for
from talent_scout.kernel.types import Model

JEV_MODEL = "typesafe/jev-1.14"
OPENROUTER_URL = "https://openrouter.ai/api"
MAX_STATE_BYTES = 30_000
MARKER = "…[truncated]"

# Timeouts are TypeSafeAPITimeoutError, a subclass of the connection error. 400, 401, 402 and 422 match neither list.
_RETRY_ON = (TypeSafeRateLimitError, TypeSafeInternalServerError, TypeSafeAPIConnectionError)
# A malformed 200 and a 404 (model retired) won't improve on retry, but the LLM can still answer.
_FALLBACK_ON = _RETRY_ON + (TypeSafeAPIResponseValidationError, TypeSafeNotFoundError)

_FALLBACK_SYSTEM = "You answer yes/no questions about the given state, each one independently."


class Judgement(Model):
    outcome: bool
    p_yes: float
    cut: float
    model: str
    source: Literal["jev", "llm_fallback"]
    # True when the state was shortened to fit; the calling stage logs a Caveat.
    truncated: bool
    reason: str | None


class _FallbackResponse(ClassifierResponse):
    reasons: dict[str, str]


def _size(state: dict) -> int:
    return len(json.dumps(state, separators=(",", ":"), ensure_ascii=False).encode())


def _longest_string(node, best=None):
    """Locate the longest string as (container, key) so it can be replaced in place."""
    for key, value in node.items() if isinstance(node, dict) else enumerate(node):
        if isinstance(value, str):
            if best is None or len(value) > len(best[0][best[1]]):
                best = (node, key)
        elif isinstance(value, (dict, list)):
            best = _longest_string(value, best)
    return best


def _fit(state: dict) -> tuple[dict, bool]:
    if _size(state) <= MAX_STATE_BYTES:
        return state, False
    state = json.loads(json.dumps(state))  # deep copy so the caller's state is untouched
    while (excess := _size(state) - MAX_STATE_BYTES) > 0:
        found = _longest_string(state)
        if found is None or len(found[0][found[1]]) <= len(MARKER):
            break  # nothing left to shorten; send as is rather than raise
        container, key = found
        text = container[key]
        container[key] = text[: max(len(text) - excess - len(MARKER), 0)] + MARKER
    return state, True


class _Slots:
    """Process-wide cap on Jev requests."""

    def __init__(self, size: int):
        self._size, self._loop, self._sem = size, None, None

    def get(self) -> asyncio.Semaphore:
        # A semaphore binds to the loop that first waits on it, so rebuild it when the loop changes.
        loop = asyncio.get_running_loop()
        if self._loop is not loop:
            self._loop, self._sem = loop, asyncio.Semaphore(self._size)
        return self._sem


def build_chain(classifier: Runnable, *, concurrency: int, fallback: Runnable | None = None) -> Runnable:
    slots = _Slots(concurrency)

    async def call(request, config: RunnableConfig):
        # The slot is held per attempt, not across backoff sleeps.
        async with slots.get():
            return await classifier.ainvoke(request, config)

    primary = RunnableLambda(call).with_retry(
        retry_if_exception_type=_RETRY_ON, wait_exponential_jitter=llm._BACKOFF, stop_after_attempt=llm.RETRIES
    )
    if fallback is None:
        return primary
    # Anything outside _FALLBACK_ON, and any error from the fallback itself, propagates unchanged.
    return primary.with_fallbacks([fallback], exceptions_to_handle=_FALLBACK_ON)


class _Verdict(Model):
    answer: bool = Field(description="True for yes, false for no.")
    reason: str = Field(description="One short sentence explaining the answer.")


def llm_fallback(tiers: Tiers) -> Runnable:
    """Answers the same request with the cheap LLM tier, as a 0-or-1 probability."""

    async def run(request, config: RunnableConfig) -> _FallbackResponse:
        questions: dict[str, Noul] = request["questions"]
        verdicts = create_model("Verdicts", __base__=Model, **{qid: (_Verdict, ...) for qid in questions})
        lines = [f"State:\n{json.dumps(request['state'], ensure_ascii=False)}\n\nQuestions:"]
        for qid, q in questions.items():
            criteria = f" Criteria: {q.criteria.model_dump_json(exclude_none=True)}" if q.criteria else ""
            lines.append(f"- {qid}: {q.instructions}{criteria}")
        out = await tiers.structured("cheap", verdicts, system=_FALLBACK_SYSTEM, name="jev_fallback").ainvoke(
            "\n".join(lines), config
        )
        got = {qid: getattr(out, qid) for qid in questions}
        return _FallbackResponse(
            model="llm:cheap",
            answers={qid: NoulAnswer(type="noul", noul=1.0 if v.answer else 0.0) for qid, v in got.items()},
            reasons={qid: v.reason for qid, v in got.items()},
        )

    return RunnableLambda(run)


class Jev:
    def __init__(self, classifier: Runnable, cuts: dict[str, dict[Placement, float]], replay: Replay | None = None):
        missing = [f"{m}/{p}" for m, per in cuts.items() for p in PLACEMENTS if p not in per]
        if missing:
            raise ValueError(f"missing cuts: {', '.join(missing)}")
        self._classifier, self._cuts, self._replay = classifier, cuts, replay
        self._chain_key = ",".join(cuts)

    async def judge(self, placement: Placement, state: dict, questions: dict[str, Noul]) -> dict[str, Judgement]:
        state, truncated = _fit(state)
        resp = await self._respond(placement, {"state": state, "questions": questions})
        cut = cut_for(self._cuts, resp.model, placement)
        reasons = resp.reasons if isinstance(resp, _FallbackResponse) else {}
        source = "llm_fallback" if isinstance(resp, _FallbackResponse) else "jev"
        out = {}
        for qid in questions:
            p_yes = resp.nouls[qid].noul
            out[qid] = Judgement(
                outcome=p_yes >= cut, p_yes=p_yes, cut=cut, model=resp.model,
                source=source, truncated=truncated, reason=reasons.get(qid),
            )
        return out

    async def _respond(self, placement: Placement, request: dict) -> ClassifierResponse:
        key = json.dumps(
            {"state": request["state"], "questions": {k: q.model_dump(mode="json", exclude_none=True) for k, q in request["questions"].items()}},
            sort_keys=True,
        )
        if self._replay and (hit := self._replay.get_jev(self._chain_key, key)):
            data = json.loads(hit)
            return (_FallbackResponse if "reasons" in data else ClassifierResponse).model_validate(data)
        config: RunnableConfig = {
            "run_name": f"jev:{placement}",
            "tags": ["jev", f"placement:{placement}"],
            "metadata": {"placement": placement, "cuts": {m: per[placement] for m, per in self._cuts.items()}},
        }
        resp = await self._classifier.ainvoke(request, config)
        if self._replay:
            self._replay.put_jev(self._chain_key, key, resp.model_dump_json())
        return resp


def make_jev(settings: Settings, tiers: Tiers | None = None) -> Jev:
    classifier = TypeSafeClassifier(
        model=JEV_MODEL, api_key=settings.openrouter_api_key, base_url=OPENROUTER_URL
    )
    chain = build_chain(
        classifier,
        concurrency=settings.jev_concurrency,
        fallback=llm_fallback(tiers or make_tiers(settings)),
    )
    replay = open_replay(settings.replay_cache) if settings.replay_cache else None
    return Jev(chain, CUTS, replay)
