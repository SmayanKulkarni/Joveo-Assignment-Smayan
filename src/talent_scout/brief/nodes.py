from collections import Counter

from talent_scout.brief.markdown import render_markdown
from talent_scout.brief.rules import default_outlook, empty_draft, match_totals
from talent_scout.brief.types import ClientRecommendations, Confidence, MarketBrief, RunNotes
from talent_scout.gateway.types import ATTRIBUTION
from talent_scout.kernel.state import LogKind, State, log
from talent_scout.kernel.types import Evidence, Source
from talent_scout.runtime.deps import Deps, Node, Router

MAX_REVISIONS = 2  # the loop stops here even if the critic still flags an Insight


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
        caveats=[e.message for e in state.run_log if e.kind == LogKind.caveat],
        attribution=f"Jobs data provided by {ATTRIBUTION[Source.adzuna]}" if has_adzuna else None,
    )


def after_critic(state: State) -> str:
    done = all(v.supported for v in state.critic_verdicts) or state.revisions >= MAX_REVISIONS
    return "render" if done else "write_brief"


def make_nodes(deps: Deps) -> dict[str, Node]:
    async def write_brief(state: State) -> dict:
        if state.stats.sample_size > 0:
            raise NotImplementedError("Briefs for a Sample with Postings are not built yet")
        draft = empty_draft(state.hiring_request)
        return {"brief_draft": draft, **log(state, "write_brief", LogKind.note, "0 Insights from the empty draft", insights=0, draft="empty")}

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
            insights=[],  # write_brief gives a draft with Insights only for a Sample it can't yet write for
            recommendations=ClientRecommendations(job_title=None, salary_band=None, top_skills=None),
            outlook=default_outlook(state.stats.sample_size),
            run_notes=_run_notes(state),
            stats=state.stats,
        )
        tags = Counter(i.confidence for i in brief.insights)
        note = log(state, "render", LogKind.note, f"{len(brief.insights)} Insights", **{c.value: tags[c] for c in Confidence})
        return {"brief": brief, "brief_markdown": render_markdown(brief, state.sample_postings), **note}

    return {"write_brief": write_brief, "critic": critic, "render": render}


ROUTERS: dict[str, Router] = {"critic": after_critic}
