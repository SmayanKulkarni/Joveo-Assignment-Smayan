import asyncio
from typing import Annotated

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, InjectedToolArg, tool
from langgraph.graph import END
from langgraph.types import interrupt
from pydantic import ValidationError

from talent_scout.collection.prompts import BROADEN_SYSTEM, FETCH_SYSTEM, RELEVANT_NOUL
from talent_scout.collection.types import FetchRecord, LowDataPayload
from talent_scout.gateway.coalesce import coalesce
from talent_scout.gateway.types import CacheStatus, Fetch, GatewayError
from talent_scout.kernel.events import emit
from talent_scout.kernel.state import LogKind, RunLogEntry, State, log, log_entry
from talent_scout.kernel.types import Posting, SearchPlan, Source
from talent_scout.runtime.deps import Deps, Node, Router
from talent_scout.runtime.pause import LowDataPause

MAX_FETCHES = 6  # per Attempt; 3 Attempts spend at most 18 of Adzuna's 25 daily calls, retries aside
MAX_BROADENS = 2  # so 3 Attempts before low_data_review
RAW_FACTOR = 1.5  # the model can't see relevance, so it gathers more raw Postings than the target
MAX_SAMPLE_TITLES = 5
MAX_REJECTED_TITLES = 10
OLD_DAYS = 30


def _fetch_for(plan: SearchPlan, title: str, page: int = 1) -> Fetch:
    return Fetch(
        title=title, page=page, country=plan.country, location=plan.location, radius_km=plan.radius_km,
        max_days_old=plan.max_days_old, category=plan.category,
    )


def _make_tools(gateway) -> dict[str, BaseTool]:
    async def search(source: Source, title: str, page: int, plan: SearchPlan, attempt: int) -> FetchRecord:
        # Built outside the try: a bad Fetch is a ValidationError for the executor, not a failed source.
        fetch = _fetch_for(plan, title, page)
        try:
            return FetchRecord(attempt=attempt, source=source, fetch=fetch, result=await gateway.fetch(fetch, source), error=None)
        except GatewayError as e:  # SourceRejected is a bug and is not caught, so it stops the Run
            return FetchRecord(attempt=attempt, source=source, fetch=fetch, result=None, error=str(e))

    # plan and attempt are injected so the model can't drift from the plan the user approved.
    @tool
    async def search_adzuna(
        title: str, plan: Annotated[SearchPlan, InjectedToolArg], attempt: Annotated[int, InjectedToolArg], page: int = 1
    ) -> FetchRecord:
        """Search Adzuna, a worldwide aggregator of private-sector job ads, by title. Honours every plan field. Metered: a small daily quota shared by every Run, so spend calls on titles that matter. One call returns one page of up to 50."""
        return await search(Source.adzuna, title, page, plan, attempt)

    @tool
    async def search_usajobs(
        title: str, plan: Annotated[SearchPlan, InjectedToolArg], attempt: Annotated[int, InjectedToolArg], page: int = 1
    ) -> FetchRecord:
        """Search USAJOBS, the US federal government's own job ads, by title. US searches only, and it ignores the plan's category. Free and unmetered, but federal roles only, so a private-sector title may return little. One call returns one page of up to 50."""
        return await search(Source.usajobs, title, page, plan, attempt)

    return {t.name: t for t in (search_adzuna, search_usajobs)}


def _bound(tools: dict[str, BaseTool], plan: SearchPlan) -> list[BaseTool]:
    # The model is never offered a tool that can't work: USAJOBS covers the US only.
    return list(tools.values()) if plan.country == "us" else [tools["search_adzuna"]]


def _tool_count(state: State) -> int:
    # Every ToolMessage counts, refusals and bad args included, so the cap is one line.
    return sum(isinstance(m, ToolMessage) for m in state.messages)


def _attempt(state: State) -> int:
    # No counter to drift: a user-driven broaden counts like any other.
    return len(state.broadened_plans)


def _current(state: State) -> list[FetchRecord]:
    return [r for r in state.fetches if r.attempt == _attempt(state)]


def _total(record: FetchRecord) -> int | None:
    return record.result.sources[record.source].total if record.result else None


def _settings(f: Fetch) -> tuple:
    return f.country, f.location, f.radius_km, f.max_days_old, f.category


def _already_searched(state: State) -> list[str]:
    here = _settings(_fetch_for(state.current_plan, "x"))
    return [
        f'- {r.source} "{r.fetch.title}" page {r.fetch.page}: {_total(r):,} matches'
        for r in state.fetches
        if r.result and _settings(r.fetch) == here
    ]


def _fetch_input(state: State) -> str:
    plan = state.current_plan
    lines = [
        f"Search plan: {plan.model_dump_json()}",
        f"Raw goal: about {round(RAW_FACTOR * plan.target_postings)} Postings across all searches.",
        f"Sample so far: {len(state.sample)} relevant Postings, target {plan.target_postings}.",
    ]
    if searched := _already_searched(state):
        lines += ["Already searched with these settings, so do not repeat:", *searched]
    return "\n".join(lines)


def _summary(record: FetchRecord, new: int) -> str:
    head = f'{record.source} "{record.fetch.title}" page {record.fetch.page}:'
    if record.result is None:
        return f"{head}\n{record.source} failed: {record.error}."
    outcome = record.result.sources[record.source]
    left = f", {outcome.calls_left} calls left" if record.source == Source.adzuna and outcome.calls_left is not None else ""
    titles = "; ".join(p.title for p in record.result.postings[:MAX_SAMPLE_TITLES]) or "none"
    return f"{head} {len(record.result.postings)} Postings, {new} new.\nAbout {outcome.total:,} matches{left}.\nSample titles: {titles}."


def _changes(old: SearchPlan, new: SearchPlan) -> str:
    diffs = [f"{k}: {getattr(old, k)} -> {getattr(new, k)}" for k in SearchPlan.model_fields if getattr(old, k) != getattr(new, k)]
    return "; ".join(diffs) or "nothing changed"


def _broaden_input(state: State) -> str:
    plan = state.current_plan
    lines = [
        f"Hiring request: {state.hiring_request.model_dump_json()}",
        f"Current plan: {plan.model_dump_json()}",
        f"Sample: {len(state.sample)} relevant Postings, target {plan.target_postings}.",
        "Searches so far and their source totals:",
    ]
    for r in state.fetches:
        found = f"{_total(r):,} matches" if r.result else f"failed: {r.error}"
        lines.append(f'- {r.source} "{r.fetch.title}" page {r.fetch.page}: {found}')
    rejected = [p.title for k, p in state.postings.items() if not state.relevance_verdicts.get(k, True)]
    if rejected:
        lines += ["Titles rejected as not the role:", *(f"- {t}" for t in rejected[:MAX_REJECTED_TITLES])]
    if state.low_data_guidance:
        lines += [f"User guidance: {state.low_data_guidance}"]
    return "\n".join(lines)


def _blocked(state: State, deps: Deps) -> str | None:
    current = _current(state)
    if current and all(r.error for r in current):
        return "Every search in this Attempt failed: " + "; ".join(dict.fromkeys(r.error for r in current))
    # Skipped under replay, or a recorded Run could take a different route when replayed.
    if (
        deps.gateway.calls_left(Source.adzuna) == 0
        and state.current_plan.country != "us"
        and not deps.settings.replay_cache
    ):
        return "Adzuna's daily limit is used up, until the next UTC day"
    return None


def _closing_caveats(state: State, node: str) -> list[RunLogEntry]:
    """Describe the Sample that actually reaches analysis, so they run once when Collection finishes."""
    sample, target = state.sample_postings, state.current_plan.target_postings
    entries = []
    if sample and (federal := sum(p.source == Source.usajobs for p in sample)) * 2 > len(sample):
        entries.append(log_entry(node, LogKind.caveat, f"Mostly federal: {federal} of {len(sample)} Postings are from USAJOBS", federal=federal))
    fetched = [o.fetched_at for r in state.fetches if r.result for o in r.result.sources.values()]
    if sample and fetched:
        # Measured from the newest fetch, never today: a clock here would change the text and miss every downstream LLM cache entry.
        newest = max(fetched).date()
        old = sum((newest - p.posted_at).days > OLD_DAYS for p in sample)
        if old * 2 > len(sample):
            entries.append(log_entry(node, LogKind.caveat, f"Old data: {old} of {len(sample)} Postings are over {OLD_DAYS} days old", old=old))
    if state.broadened_plans:
        plans = [state.search_plan, *state.broadened_plans]
        changes = [_changes(a, b) for a, b in zip(plans, plans[1:])]
        entries.append(log_entry(node, LogKind.caveat, f"Broadened {len(changes)} time(s): " + " | ".join(changes), count=len(changes)))
    if len(sample) < target:
        entries.append(log_entry(node, LogKind.caveat, f"Too few Postings: {len(sample)} relevant of a target of {target}", count=len(sample), target=target))
    return entries


def _collect_caveats(current: list[FetchRecord]) -> list[RunLogEntry]:
    outcomes = [o for r in current if r.result for o in r.result.sources.values()]
    entries = []
    # A partial L2 page names its source in `failures`; a failed call is only a failure worth a Caveat when another answered.
    failed = {s for r in current if r.result for s in r.result.failures}
    if outcomes:
        failed |= {r.source for r in current if r.error}
    if failed:
        entries.append(log_entry("collect", LogKind.caveat, f"One source failed: {', '.join(sorted(failed))}", sources=sorted(failed)))
    if dropped := sum(o.dropped for o in outcomes):
        entries.append(log_entry("collect", LogKind.caveat, f"{dropped} Postings were dropped by the source mapper", dropped=dropped))
    if replayed := [o for o in outcomes if o.cache == CacheStatus.replay]:
        oldest = min(o.fetched_at for o in replayed).isoformat()
        live = sum(o.cache == CacheStatus.miss for o in outcomes)
        entries.append(log_entry("collect", LogKind.caveat, f"Replayed data: oldest fetched {oldest}, {live} live calls during replay", oldest=oldest, live=live))
    return entries


def make_nodes(deps: Deps) -> dict[str, Node]:
    tools_by_name = _make_tools(deps.gateway)
    broaden_chain = deps.tiers.structured("strong", SearchPlan, system=BROADEN_SYSTEM, name="broaden")

    async def fetch_agent(state: State) -> dict:
        plan = state.current_plan
        if _tool_count(state) >= MAX_FETCHES:
            return log(state, "fetch_agent", LogKind.note, f"search cap of {MAX_FETCHES} reached")
        first = not state.messages
        messages = [SystemMessage(FETCH_SYSTEM), HumanMessage(_fetch_input(state))] if first else state.messages
        reply = await deps.tiers.chat("cheap", tools=_bound(tools_by_name, plan), name="fetch_agent").ainvoke(messages)
        update = {"messages": [*messages, reply]}
        if first and not reply.tool_calls:
            # A normal Attempt, not a retry path: this is rare, and collect still runs on what's there.
            update.update(log(state, "fetch_agent", LogKind.warning, "the model searched nothing in this Attempt"))
        return update

    async def tools(state: State) -> dict:
        plan = state.current_plan
        attempt = _attempt(state)
        bound ={t.name: t for t in _bound(tools_by_name, plan)}
        calls = state.messages[-1].tool_calls
        left = MAX_FETCHES - _tool_count(state)

        shown: dict[str, str] = {}  # what the card says about a failed call; the model still reads the message text

        def error(call: dict, text: str, card: str) -> ToolMessage:
            shown[call["id"]] = card
            return ToolMessage(content=text, tool_call_id=call["id"], name=call["name"], status="error")

        async def run(i: int, call: dict) -> FetchRecord | ToolMessage:
            args = call["args"]
            emit({"type": "tool_called", "name": call["name"], "summary": f'"{args.get("title")}" page {args.get("page", 1)}'})
            if i >= left:
                return error(call, f"Refused: the limit of {MAX_FETCHES} searches in this Attempt is used up.", "Skipped: search limit reached")
            if call["name"] not in bound:
                return error(call, f"Unknown tool {call['name']!r}. Available: {', '.join(bound)}.", "Didn't run")
            try:
                # Injected values go last so model output can't override them.
                return await bound[call["name"]].ainvoke({**args, "plan": plan, "attempt": attempt})
            except ValidationError as e:
                return error(call, f"Bad arguments: {e}", "Didn't run")

        outcomes = await asyncio.gather(*(run(i, c) for i, c in enumerate(calls)))

        # Counted in call order after the gather, so the summaries don't depend on which call finished first.
        seen = set(state.postings) | {p.key for r in _current(state) if r.result for p in r.result.postings}
        messages, records = [], []
        for call, outcome in zip(calls, outcomes):
            if isinstance(outcome, ToolMessage):
                messages.append(outcome)
                emit({"type": "tool_returned", "name": call["name"], "summary": shown[call["id"]]})
                continue
            keys = {p.key for p in outcome.result.postings} if outcome.result else set()
            new = len(keys - seen)
            seen |= keys
            records.append(outcome)
            messages.append(ToolMessage(content=_summary(outcome, new), tool_call_id=call["id"], name=call["name"]))
            emit({
                "type": "tool_returned", "name": call["name"],
                "summary": f"{len(keys)} Postings, {new} new" if outcome.result else "Didn't run",
            })
        return {"messages": [*state.messages, *messages], "fetches": [*state.fetches, *records]}

    async def collect(state: State) -> dict:
        current = _current(state)
        fresh = [p for r in current if r.result for p in r.result.postings]
        # By key first, so a Posting is never its own Duplicate. The first copy seen wins (Kernel 5).
        by_key = {**{p.key: p for p in fresh}, **state.postings}
        kept, merged = coalesce(list(by_key.values()))
        # The Postings are safe in `postings` now, and a second copy would be rewritten into every later checkpoint.
        stripped = [
            r.model_copy(update={"result": r.result.model_copy(update={"postings": []})}) if r in current and r.result else r
            for r in state.fetches
        ]
        totals: dict[str, dict[str, int]] = {}
        for r in current:
            if r.result and r.result.sources[r.source].cache != CacheStatus.store:  # a store total isn't the source's
                totals.setdefault(r.fetch.title, {})[r.source] = r.result.sources[r.source].total
        duplicates = sum(len(v) for v in merged.values())
        entries = [
            log_entry("collect", LogKind.note, f"kept {len(kept)} Postings, merged {duplicates} Duplicates", kept=len(kept), duplicates=duplicates),
            log_entry("collect", LogKind.note, "source totals", totals=totals),
            log_entry("collect", LogKind.result, f"Found {len(kept)} postings", kept=len(kept)),
            *_collect_caveats(current),
        ]
        return {"postings": {p.key: p for p in kept}, "fetches": stripped, "run_log": [*state.run_log, *entries]}

    def judged(state: State, p: Posting) -> dict:
        return {
            "role": state.hiring_request.role, "seniority": state.hiring_request.seniority,
            "title": p.title, "company": p.company, "domain": p.domain, "description": p.description,
        }

    async def relevance(state: State) -> dict:
        # One request per Posting: a shared request would have to fit Jev's size limit. Verdicts last across Attempts.
        fresh = [p for k, p in state.postings.items() if k not in state.relevance_verdicts]
        results = await asyncio.gather(*(deps.jev.judge("relevance", judged(state, p), {"relevant": RELEVANT_NOUL}) for p in fresh))
        verdicts = {**state.relevance_verdicts, **{p.key: r["relevant"].outcome for p, r in zip(fresh, results)}}
        update = {
            "relevance_verdicts": verdicts,
            "sample": [k for k in state.postings if verdicts[k]],
            "fetch_blocked": _blocked(state, deps),
        }
        after = state.model_copy(update=update)
        outcome = after_relevance(after)
        entries = []
        if degraded := [p.key for p, r in zip(fresh, results) if r["relevant"].source == "llm_fallback" or r["relevant"].truncated]:
            entries.append(log_entry(
                "relevance", LogKind.caveat,
                f"Jev degraded: {len(degraded)} Postings were judged by the LLM fallback or from shortened text", keys=degraded,
            ))
        entries.append(log_entry("relevance", LogKind.result, f"{len(update['sample'])} are the role"))
        entries.append(log_entry(
            "relevance", LogKind.route,
            f"{len(update['sample'])} of {len(state.postings)} Postings relevant (route: {outcome})",
        ))
        if outcome == "analyse":
            entries += _closing_caveats(after, "relevance")
        return {**update, "run_log": [*state.run_log, *entries]}

    async def broaden(state: State) -> dict:
        current = state.current_plan
        draft = await broaden_chain.ainvoke(_broaden_input(state))
        # Pinned in code, so broadening can't reach Sufficiency by lowering the target or leave the market asked about.
        # Only the user's whole-country tick may drop the place, and a blank location already means country-wide.
        location = "" if state.low_data_whole_country else current.location
        plan = draft.model_copy(update={"country": current.country, "target_postings": current.target_postings, "location": location})
        return {
            "broadened_plans": [*state.broadened_plans, plan],
            "messages": [],
            "low_data_guidance": None,  # used up, so a later broaden doesn't repeat it
            "run_log": [
                *state.run_log,
                log_entry("broaden", LogKind.note, f"broadened: {_changes(current, plan)}"),
                log_entry("broaden", LogKind.result, "Widened the search"),
            ],
        }

    async def low_data_review(state: State) -> dict:
        payload = LowDataPayload(
            count=len(state.sample), target=state.current_plan.target_postings, attempts=_attempt(state) + 1,
            plans=[state.search_plan, *state.broadened_plans], fetched=len(state.postings),
            rejected=sum(not v for v in state.relevance_verdicts.values()),
            calls_left=deps.gateway.calls_left(Source.adzuna),  # information only: it may be stale by the time the user answers
            blocked=state.fetch_blocked,
        )
        answer = interrupt(LowDataPause(payload=payload))
        entries = [log_entry("low_data_review", LogKind.pause, f"user chose {answer.action}")]
        # Only on continue: a Pause that ends in broaden would repeat them for every round.
        if answer.action == "continue":
            entries += _closing_caveats(state, "low_data_review")
        # Both are written even when null, so a stale guidance never feeds a later broaden.
        return {
            "low_data_decision": answer.action,
            "low_data_guidance": answer.guidance,
            "low_data_whole_country": answer.whole_country and answer.action == "broaden",
            "run_log": [*state.run_log, *entries],
        }

    return {
        "fetch_agent": fetch_agent,
        "tools": tools,
        "collect": collect,
        "relevance": relevance,
        "broaden": broaden,
        "low_data_review": low_data_review,
    }


def after_fetch_agent(state: State) -> str:
    return "tools" if getattr(state.messages[-1], "tool_calls", None) else "collect"


def after_relevance(state: State) -> str:
    if len(state.sample) >= state.current_plan.target_postings:
        return "analyse"
    if state.fetch_blocked or len(state.broadened_plans) >= MAX_BROADENS:
        return "low_data_review"
    return "broaden"


def after_low_data(state: State) -> str:
    if state.low_data_decision == "abort":
        return END
    return "broaden" if state.low_data_decision == "broaden" else "analyse"


ROUTERS: dict[str, Router] = {
    "fetch_agent": after_fetch_agent,
    "relevance": after_relevance,
    "low_data_review": after_low_data,
}
