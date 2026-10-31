from collections import Counter

from talent_scout.brief.markdown import render_markdown
from talent_scout.brief.prompts import WRITE_SYSTEM
from talent_scout.brief.rules import (
    build_insights, checked_draft, empty_draft, fmt_value, insight_cap, match_totals, outlook, recommendations, rule_draft,
)
from talent_scout.brief.types import BriefDraft, Confidence, MarketBrief, RunNotes
from talent_scout.gateway.types import ATTRIBUTION
from talent_scout.kernel.llm import LLMExhausted
from talent_scout.kernel.state import LogKind, State, log
from talent_scout.kernel.types import Evidence, Source
from talent_scout.runtime.deps import Deps, Node, Router

MAX_REVISIONS = 2  # the loop stops here even if the critic still flags an Insight
WRITE_MAX_TOKENS = 4096  # the largest real reply was 2,476, and this limits a runaway's cost
RULE_CAVEAT = "Brief written by rule: every model's draft failed its checks, so Insights state computed figures directly"


def _caveats(state: State) -> list[str]:
    return [e.message for e in state.run_log if e.kind == LogKind.caveat]


def _writer_input(state: State, cap: int) -> str:
    # The order is fixed so a replay matches. Posting text and keys are never sent.
    rated = outlook(state.stats, state.hiring_request)
    stats = [f"{s.id} | {s.label} | {fmt_value(s.value)} | {s.unit or ''}" for s in state.stats.stats]
    return "\n".join([
        state.hiring_request.model_dump_json(),
        f"Focus: {', '.join(d.value for d in state.focus) or 'none'}",
        f"Maximum Insights: {cap}",
        # A default rating isn't a finding, and the writer repeats it as one.
        f"Outlook: {rated.rating.value.replace('_', ' ') if rated.stat_ids else 'not rated'}",
        "Caveats:",
        *(f"- {c}" for c in _caveats(state)),
        "Stats (id | label | value | unit):",
        *stats,
    ])


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

    async def write_brief(state: State) -> dict:
        if state.stats.sample_size == 0:
            return drafted(state, empty_draft(state.hiring_request), "empty")

        request, cap = state.hiring_request, insight_cap(state.stats.sample_size)
        # Built per Run because the checks close over this Run's Stats.
        schema = checked_draft(state.stats, " ".join([request.role, request.location, *_caveats(state)]), cap)
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
        # A pass-through until the real critic lands: no verdicts, so after_critic goes to render.
        return log(state, "critic", LogKind.route, "No Insights judged, going to render", outcome="render")

    async def render(state: State) -> dict:
        draft = state.brief_draft
        brief = MarketBrief(
            hiring_request=state.hiring_request,
            replayed=deps.settings.replay_cache is not None,
            summary=draft.summary,
            summary_stat_ids=draft.summary_stat_ids,
            insights=build_insights(state.stats, state.sample_postings, draft.insights, [v.supported for v in state.critic_verdicts]),
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
