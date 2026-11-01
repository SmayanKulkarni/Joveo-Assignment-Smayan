from datetime import UTC, date, datetime

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from talent_scout.collection.types import FetchRecord
from talent_scout.gateway.testing import FakeGateway
from talent_scout.gateway.types import CacheStatus, Fetch, FetchResult, SourceOutcome
from talent_scout.kernel.jev import Jev
from talent_scout.kernel.llm import Tiers
from talent_scout.kernel.state import State
from talent_scout.kernel.testing import FakeToolChatModel, fake_classifier, make_settings
from talent_scout.kernel.thresholds import CUTS
from talent_scout.kernel.types import HiringRequest, Posting, SearchPlan, Source
from talent_scout.runtime.deps import Deps

FETCHED_AT = datetime(2026, 1, 20, tzinfo=UTC)


class Scripted(FakeToolChatModel):
    """Replays AIMessages (or JSON strings) in order and keeps every prompt it was sent. An Exception item is raised."""

    script: list = Field(default_factory=list)
    seen: list = Field(default_factory=list)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(messages)
        reply = self.script.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=reply) if isinstance(reply, str) else reply)])


def search_call(title: str, *, tool: str = "search_adzuna", page: int = 1, id: str = "c1") -> dict:
    return {"name": tool, "args": {"title": title, "page": page}, "id": id, "type": "tool_call"}


def ai_calls(*calls: dict) -> AIMessage:
    return AIMessage(content="", tool_calls=list(calls))


def plan(**over) -> SearchPlan:
    base = dict(titles=["Data Analyst"], country="in", locations=["Bangalore"], radius_km=25, max_days_old=30, target_postings=20, category=None)
    return SearchPlan(**{**base, **over})


def request() -> HiringRequest:
    return HiringRequest(
        role="Data Analyst", location="Bangalore", country="in", seniority="Senior", employment_type=None,
        work_mode=None, currency=None, purpose=None,
    )


def posting(id: str, *, title: str = "Data Analyst", source: Source = Source.adzuna, posted: date = date(2026, 1, 15), company: str | None = None, description: str | None = None) -> Posting:
    return Posting(
        source=source, source_id=id, title=title, company=company or f"Company {id}", location="Bangalore", region=("India",),
        domain=None, posted_at=posted, closes_at=None, description=description or f"Unique description for posting {id} with its own words",
        url=f"https://example.com/{id}", salary=None,
    )


def result(
    postings: list[Posting], *, source: Source = Source.adzuna, total: int | None = None, cache: CacheStatus = CacheStatus.miss,
    calls_left: int | None = 20, dropped: int = 0, fetched_at: datetime = FETCHED_AT, failures: dict | None = None,
) -> FetchResult:
    outcome = SourceOutcome(total=len(postings) if total is None else total, dropped=dropped, cache=cache, fetched_at=fetched_at, calls_left=calls_left)
    return FetchResult(postings=postings, merged={}, sources={source: outcome}, failures=failures or {})


def record(
    postings: list[Posting] | None = None, *, title: str = "data analyst", source: Source = Source.adzuna, attempt: int = 0,
    error: str | None = None, page: int = 1, the_plan: SearchPlan | None = None, **result_args,
) -> FetchRecord:
    p = the_plan or plan()
    fetch = Fetch(
        title=title, page=page, country=p.country, location=(p.locations or [""])[0], radius_km=p.radius_km,
        max_days_old=p.max_days_old, category=p.category,
    )
    res = None if error else result(postings or [], source=source, **result_args)
    return FetchRecord(attempt=attempt, source=source, fetch=fetch, result=res, error=error)


def state_with(**over) -> State:
    base = dict(request_text="Data Analyst, Bangalore", hiring_request=request(), search_plan=plan())
    return State(**{**base, **over})


def make_deps(cheap=(), strong=(), classifier=None, results=(), **settings):
    """Deps whose models and gateway are scripted; returns the models and gateway to inspect afterwards."""
    cheap_model = Scripted(messages=iter([]), script=list(cheap))
    strong_model = Scripted(messages=iter([]), script=list(strong))
    s = make_settings(**settings)
    gateway = FakeGateway(list(results))
    classifier = classifier or fake_classifier({"relevant": 1.0})
    deps = Deps(Tiers({"cheap": [cheap_model], "strong": [strong_model]}, s), Jev(classifier, CUTS), gateway, s)
    return deps, cheap_model, strong_model, gateway
