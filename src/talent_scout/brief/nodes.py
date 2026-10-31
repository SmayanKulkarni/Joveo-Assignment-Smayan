import asyncio
from collections import Counter

from talent_scout.brief.markdown import render_markdown
from talent_scout.brief.prompts import CRITIC_NOUL, REVISE_SYSTEM, WRITE_SYSTEM
from talent_scout.brief.rules import (
    build_insights, checked_draft, checked_revision, empty_draft, fmt_value, insight_cap, match_totals, outlook, recommendations, rule_draft,
)
from talent_scout.brief.types import BriefDraft, Confidence, InsightDraft, InsightVerdict, MarketBrief, RunNotes
from talent_scout.gateway.types import ATTRIBUTION
from talent_scout.kernel.llm import LLMExhausted
from talent_scout.kernel.state import LogKind, State, log, log_entry
from talent_scout.kernel.text import plural
from talent_scout.kernel.types import Evidence, Source
from talent_scout.runtime.deps import Deps, Node, Router

MAX_REVISIONS = 2  # the loop stops here even if the critic still flags an Insight
WRITE_MAX_TOKENS = 4096  # the largest real reply was 2,476, and this limits a runaway's cost
RULE_CAVEAT = "Brief written by rule: every model's draft failed its checks, so Insights state computed figures directly"


def _caveats(state: State) -> list[str]:
    return [e.message for e in state.run_log if e.kind == LogKind.caveat]


def _known_text(state: State) -> str:
    # Text whose figures the writer may repeat besides the Stats.
    request = state.hiring_request
    return " ".join([request.role, request.location, *_caveats(state)])


def _stat_lines(state: State) -> list[str]:
    return [f"{s.id} | {s.label} | {fmt_value(s.value)} | {s.unit or ''}" for s in state.stats.stats]


def _writer_input(state: State, cap: int) -> str:
    # The order is fixed so a replay matches. Posting text and keys are never sent.
    rated = outlook(state.stats, state.hiring_request)
    return "\n".join([
        state.hiring_request.model_dump_json(),
        f"Focus: {', '.join(d.value for d in state.focus) or 'none'}",
        f"Maximum Insights: {cap}",
        # A default rating isn't a finding, and the writer repeats it as one.
        f"Outlook: {rated.rating.value.replace('_', ' ') if rated.stat_ids else 'not rated'}",
        "Caveats:",
        *(f"- {c}" for c in _caveats(state)),
        "Stats (id | label | value | unit):",
        *_stat_lines(state),
    ])


def _revise_input(state: State, flagged: list[InsightDraft]) -> str:
    return "\n".join([
        "Caveats:",
        *(f"- {c}" for c in _caveats(state)),
        "Stats (id | label | value | unit):",
        *_stat_lines(state),
        "Flagged Insights (text | cited ids):",
        *(f"- {i.text} | {', '.join(i.stat_ids)}" for i in flagged),
    ])


def _claim(state: State, insight: InsightDraft) -> dict:
    # Jev sees only the Stats the claim cites, never Posting text, so the question is about Stats.
    by_id = {s.id: s for s in state.stats.stats}
    return {
        "hiring_request": state.hiring_request.model_dump(mode="json"),
        "caveats": _caveats(state),
        "claim": insight.text,
        "stats": [
            {"id": s.id, "label": s.label, "value": fmt_value(s.value), "unit": s.unit}
            for s in (by_id[i] for i in insight.stat_ids)
        ],
    }


def _run_notes(state: State) -> RunNotes:
    has_adzuna = any(p.source == Source.adzuna for p in state.sample_postings)
    return RunNotes(
        questions=state.questions,
        assumptions=state.assumptions,
        focus=state.focus,
        final_plan=state.current_plan,
        # The first plan and every broadened one before the last, which is the final plan.
        earlier_plans=[state.search_plan, *state.broadened_plans[:-1]] if state.broadened_plans else [],
        postings_analysed=Evidence(posting_keys=state.sample),
        match_totals=match_totals(state.run_log),
        caveats=_caveats(state),
        attribution=f"Jobs data provided by {ATTRIBUTION[Source.adzuna]}" if has_adzuna else None,
    )


def after_critic(state: State) -> str:
    done = all(v.supported for v in state.critic_verdicts) or state.revisions >= MAX_REVISIONS
    return "render" if done else "write_brief"


def make_nodes(deps: Deps) -> dict[str, Node]:
    def drafted(state: State, draft: BriefDraft, kind: str, entry=LogKind.note, message: str | None = None) -> dict:
        message = message or f"{len(draft.insights)} Insights from the {kind} draft"
        return {"brief_draft": draft, **log(state, "write_brief", entry, message, insights=len(draft.insights), draft=kind)}

    async def revise(state: State) -> dict:
        draft = state.brief_draft
        pairs = list(zip(draft.insights, state.critic_verdicts))
        kept = [(i, v) for i, v in pairs if v.supported]
        flagged = [i for i, v in pairs if not v.supported]

        # Only the room the kept Insights leave, so a revision can't push the Brief over its cap.
        schema = checked_revision(state.stats, _known_text(state), insight_cap(state.stats.sample_size) - len(kept), [i.text for i, _ in kept])
        chain = deps.tiers.structured("strong", schema, system=REVISE_SYSTEM, name="revise", max_tokens=WRITE_MAX_TOKENS)
        try:
            out = await chain.ainvoke(_revise_input(state, flagged))
        except LLMExhausted as e:
            if not e.bad_output:
                raise
            # The draft stands and the critic has nothing new to judge, so the loop ends here.
            return {"revisions": MAX_REVISIONS}
        # Kept Insights come first and untouched, so the verdicts still line up with the start of the draft.
        revised = draft.model_copy(update={"insights": [*(i for i, _ in kept), *out.insights]})
        return {
            **drafted(state, revised, "revision"),
            "critic_verdicts": [v for _, v in kept],
            "revisions": state.revisions + 1,
        }

    async def write_brief(state: State) -> dict:
        if state.stats.sample_size == 0:
            return drafted(state, empty_draft(state.hiring_request), "empty")

        if state.brief_draft and state.critic_verdicts:
            return await revise(state)

        cap = insight_cap(state.stats.sample_size)
        # Built per Run because the checks close over this Run's Stats.
        schema = checked_draft(state.stats, _known_text(state), cap)
        chain = deps.tiers.structured("strong", schema, system=WRITE_SYSTEM, name="write_brief", max_tokens=WRITE_MAX_TOKENS)
        try:
            out = await chain.ainvoke(_writer_input(state, cap))
        except LLMExhausted as e:
            if not e.bad_output:
                raise  # a rerun might work, so `scout resume` retries only this node
            # Bad output would repeat, so the revision budget is spent and no further LLM call is made.
            return {**drafted(state, rule_draft(state.stats), "rule", LogKind.caveat, RULE_CAVEAT), "revisions": MAX_REVISIONS}
        # A checkpoint stores the class path, and the checked subclass is local.
        return drafted(state, BriefDraft.model_validate(out.model_dump()), "llm")

    async def critic(state: State) -> dict:
        # Only Insights past the verdicts are new; kept ones were judged on an earlier pass.
        fresh = state.brief_draft.insights[len(state.critic_verdicts):]
        results = await asyncio.gather(*(deps.jev.judge("critic", _claim(state, i), {"supported": CRITIC_NOUL}) for i in fresh))
        judged = [r["supported"] for r in results]
        update = {"critic_verdicts": [*state.critic_verdicts, *(InsightVerdict(supported=j.outcome, p_yes=j.p_yes) for j in judged)]}
        outcome = after_critic(state.model_copy(update=update))

        entries = []
        if degraded := sum(j.source == "llm_fallback" or j.truncated for j in judged):
            entries.append(log_entry(
                "critic", LogKind.caveat, f"Critic degraded: {plural(degraded, 'Insight')} judged by the LLM fallback or from shortened text",
            ))
        supported = sum(j.outcome for j in judged)
        entries.append(log_entry(
            "critic", LogKind.route, f"{supported} of {len(judged)} Insights supported (route: {outcome})",
            scores=[j.p_yes for j in judged], outcome=outcome,
        ))
        return {**update, "run_log": [*state.run_log, *entries]}

    async def render(state: State) -> dict:
        draft = state.brief_draft
        verdicts = [v.supported for v in state.critic_verdicts]
        # Logged first so the Run Notes include it.
        if unconfirmed := verdicts.count(False):
            caveat = log_entry("render", LogKind.caveat, f"Insights not confirmed: {plural(unconfirmed, 'Insight')} could not be confirmed by the critic and {'is' if unconfirmed == 1 else 'are'} capped at Medium")
            state = state.model_copy(update={"run_log": [*state.run_log, caveat]})
        brief = MarketBrief(
            hiring_request=state.hiring_request,
            replayed=deps.settings.replay_cache is not None,
            summary=draft.summary,
            summary_stat_ids=draft.summary_stat_ids,
            insights=build_insights(state.stats, state.sample_postings, draft.insights, verdicts),
            recommendations=recommendations(state.stats, state.hiring_request, state.sample_postings),
            outlook=outlook(state.stats, state.hiring_request),
            run_notes=_run_notes(state),
            stats=state.stats,
        )
        tags = Counter(i.confidence for i in brief.insights)
        note = log(state, "render", LogKind.note, f"{len(brief.insights)} Insights", **{c.value: tags[c] for c in Confidence})
        return {"brief": brief, "brief_markdown": render_markdown(brief, state.sample_postings), **note}

    return {"write_brief": write_brief, "critic": critic, "render": render}


ROUTERS: dict[str, Router] = {"critic": after_critic}
