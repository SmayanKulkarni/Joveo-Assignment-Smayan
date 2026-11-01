import asyncio
from datetime import date

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langgraph.config import get_config
from langgraph.graph import END
from langgraph.types import Send, interrupt

from talent_scout.analysis.types import EmployerType, ExtractBatch, Extraction, Requirement, Seniority, SkillMention
from talent_scout.brief.markdown import render_markdown
from talent_scout.brief.nodes import _run_notes, after_critic
from talent_scout.brief.types import (
    BandRecommendation, BriefDraft, ClientRecommendations, Confidence, HiringOutlook, Insight, InsightDraft,
    InsightVerdict, MarketBrief, OutlookRating, RunNotes, SkillsRecommendation, TitleRecommendation,
)
from talent_scout.collection.nodes import after_fetch_agent
from talent_scout.collection.types import LowDataPayload
from talent_scout.kernel.events import emit
from talent_scout.kernel.state import LogKind, State, log, log_entry
from talent_scout.kernel.types import (
    Assumption, ClarifyingQuestion, Dimension, Evidence, HiringRequest, MarketStats, Posting, RequestField, Salary,
    PayPeriod, SearchPlan, Source, Stat,
)
from talent_scout.request_plan.nodes import after_review
from talent_scout.request_plan.types import ClarifyPayload, PlanAction, PlanReviewPayload
from talent_scout.runtime.deps import Node, Router
from talent_scout.runtime.pause import ClarifyPause, LowDataPause, PlanReviewPause

DEMO_LOCATION = "Austin, Texas"
DEMO_CAVEAT = "Demo data: these Postings are invented for the walkthrough"
# Words per second of streamed text, as a share of a node's delay.
WORDS_PER_DELAY = 8


def _posting(source: Source, source_id: str, title: str, company: str, low: int, high: int, predicted: bool = False) -> Posting:
    return Posting(
        source=source, source_id=source_id, title=title, company=company, location=DEMO_LOCATION,
        region=("US", "Texas", "Austin"), domain="it-jobs", posted_at=date(2026, 10, 12), closes_at=None,
        description=f"{title} at {company}. Python, SQL and a cloud warehouse.", url=f"https://example.com/jobs/{source_id}",
        salary=Salary(min=low, max=high, currency="USD", period=PayPeriod.annual, predicted=predicted),
    )


POSTINGS = [
    _posting(Source.adzuna, "a1", "Data Engineer", "Northwind Analytics", 105_000, 125_000),
    _posting(Source.adzuna, "a2", "Senior Data Engineer", "Lone Star Health", 130_000, 155_000),
    _posting(Source.adzuna, "a3", "Data Platform Engineer", "Brightline Energy", 110_000, 130_000, predicted=True),
    _posting(Source.adzuna, "a4", "Analytics Engineer", "Riverbend Bank", 100_000, 120_000),
    _posting(Source.usajobs, "u1", "IT Specialist (Data Management)", "Department of Veterans Affairs", 98_000, 128_000),
    _posting(Source.adzuna, "a5", "Lead Data Engineer", "Pecan Street Labs", 140_000, 165_000, predicted=True),
]
KEYS = [p.key for p in POSTINGS]
FIRST_ATTEMPT = 3  # Postings the first search finds, too few until the plan is broadened

_QUESTION = ClarifyingQuestion(
    about=RequestField.location, text="Where will this person work?",
    options=[DEMO_LOCATION, "Remote, United States"], answer=None,
)


def _evidence(*indexes: int) -> Evidence:
    return Evidence(posting_keys=[KEYS[i] for i in indexes])


def _stat(id: str, dimension: Dimension, label: str, value: float | str, unit: str | None, evidence: Evidence) -> Stat:
    return Stat(id=id, dimension=dimension, label=label, value=value, unit=unit, evidence=evidence)


STATS = MarketStats(sample_size=len(POSTINGS), stats=[
    _stat("demand.postings", Dimension.demand, "Postings analysed", 6, "Postings", _evidence(*range(6))),
    _stat("demand.employers", Dimension.demand, "Distinct employers", 6, "employers", _evidence(*range(6))),
    _stat("comp.median", Dimension.compensation, "Median salary midpoint", 124_000, "USD per year", _evidence(*range(6))),
    _stat("skills.python", Dimension.skills, "Postings naming Python", 5, "Postings", _evidence(0, 1, 2, 3, 5)),
    _stat("skills.sql", Dimension.skills, "Postings naming SQL", 4, "Postings", _evidence(0, 1, 3, 4)),
    _stat("titles.senior", Dimension.titles_seniority, "Share of senior or lead titles", 0.33, "share", _evidence(1, 5)),
])

# What the critic first flags, and the wording that replaces it.
OVERREACH = "Python is named by every analysed Posting."
REVISED = "Python is named by 5 of the 6 analysed Postings."
_INSIGHTS = [
    ("Six employers are hiring for this role in Austin, none of them more than once.", Dimension.demand,
     ["demand.postings", "demand.employers"], _evidence(*range(6)), Confidence.high, "6 Postings from 6 employers"),
    ("The middle of the pay range is about 124,000 USD a year.", Dimension.compensation,
     ["comp.median"], _evidence(*range(6)), Confidence.medium, "Two of the salaries are estimated by the source"),
    (REVISED, Dimension.skills, ["skills.python"], _evidence(0, 1, 2, 3, 5), Confidence.low, "Only 5 Postings carry the skill"),
]
_SUMMARY = "Hiring for data engineers in Austin is steady across six employers, paying about 124,000 USD a year."


def demo_brief() -> MarketBrief:
    """A Brief with every part filled, to build the Brief view against. The Run supplies its own request and notes."""
    notes = RunNotes(
        questions=[], assumptions=[], focus=[],
        final_plan=SearchPlan(
            titles=["Data Engineer"], country="us", locations=[DEMO_LOCATION], radius_km=40, max_days_old=30,
            target_postings=20, category="it-jobs",
        ),
        earlier_plans=[], postings_analysed=_evidence(*range(6)), match_totals=[], caveats=[DEMO_CAVEAT], attribution=None,
    )
    return MarketBrief(
        hiring_request=_request(None, DEMO_LOCATION), replayed=False, summary=_SUMMARY,
        summary_stat_ids=["demand.postings", "comp.median"],
        insights=[
            Insight(text=text, dimension=dimension, stat_ids=ids, evidence=evidence, confidence=confidence, confidence_reason=reason)
            for text, dimension, ids, evidence, confidence, reason in _INSIGHTS
        ],
        recommendations=ClientRecommendations(
            job_title=TitleRecommendation(
                title="Data Engineer", reason="The most common title among the analysed Postings",
                stat_ids=["demand.postings"], evidence=_evidence(0, 1, 2, 5),
            ),
            salary_band=BandRecommendation(
                low=105_000, high=132_000, unit="USD per year", reason="The middle of the salaries stated",
                stat_ids=["comp.median"], evidence=_evidence(*range(6)),
            ),
            top_skills=SkillsRecommendation(
                skills=["Python", "SQL"], reason="Named by most Postings", stat_ids=["skills.python", "skills.sql"],
                evidence=_evidence(0, 1, 2, 3, 4, 5),
            ),
        ),
        outlook=HiringOutlook(
            rating=OutlookRating.competitive, reason="Several employers are hiring at once, and pay is rising with seniority",
            stat_ids=["demand.postings"], evidence=_evidence(*range(6)),
        ),
        run_notes=notes, stats=STATS,
    )


def _request(state: State | None, default_location: str = DEMO_LOCATION) -> HiringRequest:
    answered = state and next((q.answer for q in state.questions if q.answer), None)
    return HiringRequest(
        role=(state.request_text.strip()[:80] if state else "Data Engineer"), location=answered or default_location,
        country="us", seniority=None, employment_type=None, work_mode=None, currency=None, purpose=None,
    )


class _Scripted(BaseChatModel):
    """Streams fixed reasoning then text, so the `messages` stream mode reports it as it does a real model."""

    reasoning: str = ""
    text: str = ""
    delay: float = 0

    @property
    def _llm_type(self) -> str:
        return "demo"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.text))])

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        for kind, words in (("reasoning", self.reasoning), ("text", self.text)):
            for word in words.split():
                await asyncio.sleep(self.delay / WORDS_PER_DELAY)
                yield ChatGenerationChunk(message=AIMessageChunk(content=[{"type": kind, kind: word + " "}]))


def _sends(state: State) -> list[Send]:
    # One batch per Posting, so the extraction progress has several steps to show.
    return [Send("batch_extract", ExtractBatch(postings=[p])) for p in state.sample_postings]


def _after_clarity(state: State) -> str:
    return "clarify" if any(q.answer is None for q in state.questions) else "plan"


def _after_relevance(state: State):
    # The first Attempt always finds too few, so the low-data Pause is seen once.
    return _sends(state) if state.broadened_plans else "low_data_review"


def _after_low_data(state: State):
    if state.low_data_decision == "abort":
        return END
    return "broaden" if state.low_data_decision == "broaden" else _sends(state)


DEMO_ROUTERS: dict[str, Router] = {
    "clarity_check": _after_clarity,
    "plan_review": after_review,
    "fetch_agent": after_fetch_agent,
    "relevance": _after_relevance,
    "low_data_review": _after_low_data,
    "critic": after_critic,
}


def demo_nodes(delay: float) -> dict[str, Node]:
    failed: set[str] = set()  # Runs that already hit their one scripted failure

    async def beat() -> None:
        await asyncio.sleep(delay)

    async def say(reasoning: str = "", text: str = "") -> None:
        await _Scripted(reasoning=reasoning, text=text, delay=delay).ainvoke("")

    async def intake(state: State) -> dict:
        await beat()
        return log(state, "intake", LogKind.note, "Read the request")

    async def clarity_check(state: State) -> dict:
        await say(reasoning="The role is clear, but the place could mean a city or remote work, so one question is worth asking.")
        if not state.questions:
            return {"questions": [_QUESTION], **log(state, "clarity_check", LogKind.route, "one question to ask first")}
        assumption = Assumption(about=RequestField.seniority, value="mid-level", reason="the request doesn't say")
        return {
            "hiring_request": _request(state), "assumptions": [assumption],
            **log(state, "clarity_check", LogKind.route, "request is final"),
        }

    async def clarify(state: State) -> dict:
        pending = [q for q in state.questions if q.answer is None]
        answer = interrupt(ClarifyPause(payload=ClarifyPayload(questions=pending)))
        filled = iter(answer.answers)
        questions = [q if q.answer is not None else q.model_copy(update={"answer": next(filled, "")}) for q in state.questions]
        return {"questions": questions, **log(state, "clarify", LogKind.pause, f"answered {len(pending)} questions")}

    async def plan(state: State) -> dict:
        role = state.hiring_request.role
        await say(reasoning=f"Searching on {role} first, then the nearest neighbouring titles, within a day's commute.")
        wider = bool(state.plan_feedback)  # a rejected plan comes back with more titles and a longer window
        search_plan = SearchPlan(
            titles=[role, f"Lead {role}"] if wider else [role], country="us", locations=[state.hiring_request.location],
            radius_km=40, max_days_old=45 if wider else 30, target_postings=20, category="it-jobs",
        )
        return {"search_plan": search_plan, **log(state, "plan", LogKind.note, f"plan: {', '.join(search_plan.titles)}, target 20")}

    async def plan_review(state: State) -> dict:
        answer = interrupt(PlanReviewPause(payload=PlanReviewPayload(plan=state.search_plan, assumptions=state.assumptions, calls_left=21)))
        update = {"plan_decision": answer.action, "plan_feedback": answer.feedback}
        if answer.action == PlanAction.edit:
            update["search_plan"] = answer.plan
        return {**update, **log(state, "plan_review", LogKind.pause, f"plan {answer.action}")}

    async def fetch_agent(state: State) -> dict:
        rounds = sum(isinstance(m, ToolMessage) for m in state.messages)
        title = state.current_plan.titles[0]
        if rounds == 0:
            text, call = f"Starting with Adzuna, searching for {title}.", ("search_adzuna", "adzuna-1")
        elif rounds == 1:
            text, call = "Adzuna answered. USAJOBS may hold federal roles, so checking it too.", ("search_usajobs", "usajobs-1")
        else:
            text, call = "Both sources have answered, so the search is complete.", None
        await say(reasoning="Which source covers this role best?" if rounds == 0 else "", text=text)
        calls = [{"name": call[0], "args": {"title": title, "page": 1}, "id": call[1], "type": "tool_call"}] if call else []
        return {"messages": [*state.messages, AIMessage(content=text, tool_calls=calls)]}

    async def tools(state: State) -> dict:
        messages = []
        for call in state.messages[-1].tool_calls:
            source = call["name"].removeprefix("search_")
            emit({"type": "tool_called", "name": call["name"], "summary": f'"{call["args"]["title"]}" page 1'})
            await beat()
            cached = source == "usajobs"
            count = 14 if cached else 63
            emit({"type": "api_called", "source": source, "cached": cached, "count": count})
            emit({"type": "tool_returned", "name": call["name"], "summary": f"{count} Postings"})
            messages.append(ToolMessage(content=f"{count} Postings", tool_call_id=call["id"], name=call["name"]))
        return {"messages": [*state.messages, *messages]}

    async def collect(state: State) -> dict:
        await beat()
        found = POSTINGS if state.broadened_plans else POSTINGS[:FIRST_ATTEMPT]
        title = state.current_plan.titles[0]
        entries = [
            log_entry("collect", LogKind.note, f"kept {len(found)} Postings, merged 0 Duplicates", kept=len(found), duplicates=0),
            log_entry("collect", LogKind.note, "source totals", totals={title: {"adzuna": 1_240, "usajobs": 38}}),
            log_entry("collect", LogKind.result, f"Found {len(found)} postings", kept=len(found)),
        ]
        return {"postings": {p.key: p for p in found}, "run_log": [*state.run_log, *entries]}

    async def relevance(state: State) -> dict:
        await beat()
        message = f"{len(state.postings)} of {len(state.postings)} Postings relevant"
        return {
            "relevance_verdicts": {k: True for k in state.postings}, "sample": list(state.postings), "fetch_blocked": None,
            "run_log": [
                *state.run_log,
                log_entry("relevance", LogKind.result, f"{len(state.postings)} are the role"),
                log_entry("relevance", LogKind.route, message),
            ],
        }

    async def broaden(state: State) -> dict:
        plan = state.current_plan
        await say(reasoning="Too few Postings. A wider radius and a longer window should find more.")
        wider = plan.model_copy(update={"radius_km": 80, "max_days_old": 60})
        return {
            "broadened_plans": [*state.broadened_plans, wider], "messages": [], "low_data_guidance": None,
            "run_log": [
                *state.run_log,
                log_entry("broaden", LogKind.note, "broadened: radius_km: 40 -> 80; max_days_old: 30 -> 60"),
                log_entry("broaden", LogKind.result, "Widened the search"),
            ],
        }

    async def low_data_review(state: State) -> dict:
        payload = LowDataPayload(
            count=len(state.sample), target=state.current_plan.target_postings, attempts=len(state.broadened_plans) + 1,
            plans=[state.search_plan, *state.broadened_plans], fetched=len(state.postings), rejected=0, calls_left=21, blocked=None,
        )
        answer = interrupt(LowDataPause(payload=payload))
        entries = [log_entry("low_data_review", LogKind.pause, f"user chose {answer.action}")]
        if answer.action == "continue":
            entries.append(log_entry(
                "low_data_review", LogKind.caveat,
                f"Too few Postings: {len(state.sample)} relevant of a target of {state.current_plan.target_postings}",
            ))
        return {"low_data_decision": answer.action, "low_data_guidance": answer.guidance, "run_log": [*state.run_log, *entries]}

    async def batch_extract(batch: ExtractBatch) -> dict:
        # Staggered by position so the progress bar moves instead of jumping.
        position = KEYS.index(batch.postings[0].key) + 1
        await asyncio.sleep(delay * position / 2)
        extraction = Extraction(
            skills=[SkillMention(name="Python", requirement=Requirement.must), SkillMention(name="SQL", requirement=Requirement.nice)],
            seniority=Seniority.mid, years_min=None, employer_type=EmployerType.direct, ungrounded=0,
        )
        return {"extractions": {batch.postings[0].key: extraction}}

    async def normalise_skills(state: State) -> dict:
        await beat()
        thread_id = get_config()["configurable"]["thread_id"]
        if "fail" in state.request_text.lower() and thread_id not in failed:
            failed.add(thread_id)
            raise RuntimeError("Demo failure: Resume retries this step")
        return {"skill_aliases": {}, **log(state, "normalise_skills", LogKind.note, "2 skill names, no duplicates")}

    async def stats(state: State) -> dict:
        await beat()
        entries = [
            log_entry("stats", LogKind.note, f"{len(STATS.stats)} Stats from {STATS.sample_size} Postings"),
            log_entry("stats", LogKind.caveat, DEMO_CAVEAT),
        ]
        return {"stats": STATS, "run_log": [*state.run_log, *entries]}

    async def write_brief(state: State) -> dict:
        if state.brief_draft:  # a revision: the flagged Insight is replaced and the rest kept
            await say(reasoning="One claim goes further than the figures allow. Rewording it.")
            kept = state.brief_draft.insights[: len(state.critic_verdicts) - 1]
            draft = state.brief_draft.model_copy(update={"insights": [*kept, InsightDraft(text=REVISED, stat_ids=["skills.python"])]})
            return {
                "brief_draft": draft, "critic_verdicts": state.critic_verdicts[:-1], "revisions": state.revisions + 1,
                **log(state, "write_brief", LogKind.note, "1 Insight reworded"),
            }
        await say(reasoning="Lead with demand, then pay, then the skills most Postings ask for.")
        insights = [InsightDraft(text=text, stat_ids=ids) for text, _, ids, *_ in _INSIGHTS[:-1]]
        draft = BriefDraft(
            summary=_SUMMARY, summary_stat_ids=["demand.postings", "comp.median"],
            insights=[*insights, InsightDraft(text=OVERREACH, stat_ids=["skills.python"])],
        )
        return {"brief_draft": draft, **log(state, "write_brief", LogKind.note, f"{len(draft.insights)} Insights from the draft")}

    async def critic(state: State) -> dict:
        await say(reasoning="Checking each claim against the figures it cites.")
        fresh = state.brief_draft.insights[len(state.critic_verdicts):]
        # Only the overreaching claim fails, and only the first time.
        verdicts = [InsightVerdict(supported=i.text != OVERREACH, p_yes=0.9 if i.text != OVERREACH else 0.1) for i in fresh]
        verdicts = [*state.critic_verdicts, *verdicts]
        route = after_critic(state.model_copy(update={"critic_verdicts": verdicts}))
        supported = sum(v.supported for v in verdicts)
        return {
            "critic_verdicts": verdicts,
            **log(state, "critic", LogKind.route, f"{supported} of {len(verdicts)} Insights supported (route: {route})"),
        }

    async def render(state: State) -> dict:
        await beat()
        brief = demo_brief().model_copy(update={"hiring_request": state.hiring_request, "run_notes": _run_notes(state)})
        return {
            "brief": brief, "brief_markdown": render_markdown(brief, state.sample_postings),
            **log(state, "render", LogKind.note, f"{len(brief.insights)} Insights"),
        }

    return {
        "intake": intake, "clarity_check": clarity_check, "clarify": clarify, "plan": plan, "plan_review": plan_review,
        "fetch_agent": fetch_agent, "tools": tools, "collect": collect, "relevance": relevance, "broaden": broaden,
        "low_data_review": low_data_review, "batch_extract": batch_extract, "normalise_skills": normalise_skills,
        "stats": stats, "write_brief": write_brief, "critic": critic, "render": render,
    }
