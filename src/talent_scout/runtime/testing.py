from contextlib import asynccontextmanager

from langgraph.types import interrupt

from talent_scout.analysis.types import EmployerType, Extraction, Seniority
from talent_scout.brief.types import (
    ClientRecommendations, HiringOutlook, MarketBrief, OutlookRating, RunNotes,
)
from talent_scout.collection.types import LowDataPayload
from talent_scout.gateway.testing import FakeGateway
from talent_scout.kernel.jev import Jev
from talent_scout.kernel.llm import Tiers
from talent_scout.kernel.settings import Settings
from talent_scout.kernel.state import LogKind, State, log
from talent_scout.kernel.testing import FakeToolChatModel, fake_classifier
from talent_scout.kernel.thresholds import CUTS
from talent_scout.kernel.types import ClarifyingQuestion, Evidence, HiringRequest, MarketStats, RequestField, SearchPlan
from talent_scout.request_plan.types import ClarifyPayload, PlanReviewPayload
from talent_scout.runtime.deps import Deps, Node, Router
from talent_scout.runtime.pause import ClarifyPause, LowDataPause, PlanReviewPause

_REQUEST = HiringRequest(
    role="Stub role", location="Stub city", country="us", seniority=None, employment_type=None,
    work_mode=None, currency=None, purpose=None,
)
_PLAN = SearchPlan(
    titles=["Stub role"], country="us", location="Stub city", radius_km=0,
    max_days_old=30, target_postings=20, category=None,
)
_EXTRACTION = Extraction(skills=[], seniority=Seniority.unknown, years_min=None, employer_type=EmployerType.unknown, ungrounded=0)
_QUESTION = ClarifyingQuestion(about=RequestField.role, text="Which role?", options=["Stub role"], answer=None)


def stub_brief() -> MarketBrief:
    """The smallest valid Brief: no Postings, so no Insights and no recommendations."""
    no_evidence = Evidence(posting_keys=[])
    return MarketBrief(
        hiring_request=_REQUEST, replayed=False, summary="Stub summary", summary_stat_ids=[], insights=[],
        recommendations=ClientRecommendations(job_title=None, salary_band=None, top_skills=None),
        outlook=HiringOutlook(rating=OutlookRating.competitive, reason="Stub", stat_ids=[], evidence=no_evidence),
        run_notes=RunNotes(
            questions=[], assumptions=[], focus=[], final_plan=_PLAN, earlier_plans=[], postings_analysed=no_evidence,
            match_totals=[], caveats=[], attribution=None,
        ),
        stats=MarketStats(sample_size=0, stats=[]),
    )


def _stub(name: str, **update) -> Node:
    async def node(state: State) -> dict:
        return {**update, **log(state, name, LogKind.note, "stub")}

    return node


async def _clarify(state: State) -> dict:
    answer = interrupt(ClarifyPause(payload=ClarifyPayload(questions=[_QUESTION])))
    # The router leaves the clarify loop once questions is non-empty.
    answered = _QUESTION.model_copy(update={"answer": answer.answers[0]})
    return {"questions": [answered], **log(state, "clarify", LogKind.pause, "answered")}


async def _plan_review(state: State) -> dict:
    answer = interrupt(PlanReviewPause(payload=PlanReviewPayload(plan=state.search_plan, assumptions=[])))
    return log(state, "plan_review", LogKind.pause, f"plan {answer.action}")


async def _low_data_review(state: State) -> dict:
    payload = LowDataPayload(
        count=0, target=_PLAN.target_postings, attempts=1, plans=[_PLAN], fetched=0, rejected=0, calls_left=None, blocked=None
    )
    answer = interrupt(LowDataPause(payload=payload))
    return log(state, "low_data_review", LogKind.pause, answer.action)


def stub_nodes() -> dict[str, Node]:
    return {
        "intake": _stub("intake"),
        "clarity_check": _stub("clarity_check", hiring_request=_REQUEST),
        "clarify": _clarify,
        "plan": _stub("plan", search_plan=_PLAN),
        "plan_review": _plan_review,
        "fetch_agent": _stub("fetch_agent"),
        "tools": _stub("tools"),
        "collect": _stub("collect", postings={}),
        "relevance": _stub("relevance", sample=[]),
        "broaden": _stub("broaden", broadened_plans=[_PLAN]),
        "low_data_review": _low_data_review,
        "batch_extract": _stub("batch_extract", extractions={"stub": _EXTRACTION}),
        "normalise_skills": _stub("normalise_skills", skill_aliases={}),
        "stats": _stub("stats", stats=MarketStats(sample_size=0, stats=[])),
        "write_brief": _stub("write_brief"),
        "critic": _stub("critic"),
        "render": _stub("render", brief=stub_brief(), brief_markdown="# Stub brief"),
    }


# Walks one path, the one that visits all three Pauses.
STUB_ROUTERS: dict[str, Router] = {
    "clarity_check": lambda state: "plan" if state.questions else "clarify",
    "plan_review": lambda state: "fetch_agent",
    "fetch_agent": lambda state: "collect",
    "relevance": lambda state: "low_data_review",
    "low_data_review": lambda state: "stats",
    "critic": lambda state: "render",
}


def fake_deps(settings: Settings) -> Deps:
    fake_chain = [FakeToolChatModel(messages=iter([]))]
    return Deps(
        tiers=Tiers({"cheap": fake_chain, "strong": fake_chain}, settings),
        jev=Jev(fake_classifier({}), CUTS),
        gateway=FakeGateway([]),
        settings=settings,
        stub_stages=True,
    )


@asynccontextmanager
async def open_fake_deps(settings: Settings):
    yield fake_deps(settings)


async def pass_balance(settings: Settings) -> float:
    return float("inf")


# One valid answer per Pause, enough to walk the stub path.
ANSWER_FOR = {
    "clarify": {"answers": ["Software"]},
    "plan_review": {"action": "approve", "plan": None, "feedback": None},
    "low_data_review": {"action": "continue"},
}
