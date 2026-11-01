import asyncio
import dataclasses
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from talent_scout.brief.nodes import ROUTERS, _run_notes, after_critic, make_nodes
from talent_scout.brief.rules import match_totals
from talent_scout.brief.types import InsightVerdict
from talent_scout.kernel.state import LogKind, RunLogEntry, State
from talent_scout.kernel.testing import make_settings
from talent_scout.kernel.types import (
    Assumption, ClarifyingQuestion, Dimension, HiringRequest, MarketStats, Posting, RequestField, SearchPlan, Source,
)
from talent_scout.runtime import controller as controller_module
from talent_scout.runtime import graph as graph_module
from talent_scout.runtime.controller import RunController
from talent_scout.runtime.events import Paused
from talent_scout.runtime.graph import build_graph
from talent_scout.runtime.registry import RunStatus
from talent_scout.runtime.testing import ANSWER_FOR, STUB_ROUTERS, fake_deps, pass_balance, stub_nodes

REQUEST = HiringRequest(
    role="Data Analyst", location="Austin", country="us", seniority=None, employment_type=None,
    work_mode=None, currency=None, purpose=None,
)


def plan(title="Data Analyst", target=30) -> SearchPlan:
    return SearchPlan(
        titles=[title], country="us", locations=["Austin"], radius_km=10, max_days_old=30, target_postings=target, category=None
    )


def note(node, kind, message, **data) -> RunLogEntry:
    return RunLogEntry(node=node, kind=kind, message=message, data=data)


def zero_state(**fields) -> State:
    base = dict(
        request_text="x", hiring_request=REQUEST, search_plan=plan(), stats=MarketStats(sample_size=0, stats=[]), sample=[],
    )
    return State(**{**base, **fields})


def run_nodes(state: State, settings=None) -> dict:
    nodes = make_nodes(fake_deps(settings or make_settings()))

    async def go():
        update = await nodes["write_brief"](state)
        state2 = state.model_copy(update=update)
        return await nodes["render"](state2)

    return asyncio.run(go())


def test_zero_postings_write_brief_makes_no_llm_call_and_render_says_there_are_no_findings():
    update = run_nodes(zero_state())

    brief, md = update["brief"], update["brief_markdown"]
    assert brief.summary == "No Relevant Postings were found for Data Analyst in Austin, so this Brief has no market findings."
    assert brief.insights == [] and brief.summary_stat_ids == []
    assert brief.outlook.rating == "competitive" and brief.outlook.stat_ids == []
    assert brief.recommendations.model_dump() == {"job_title": None, "salary_band": None, "top_skills": None}
    headings = [line for line in md.splitlines() if line.startswith("#")]
    assert headings == [
        "# Market Brief: Data Analyst, Austin", "## Summary", "## Hiring Outlook", "## Client Recommendations", "## Insights",
        "## Run Notes", "## Evidence", "## Market figures", "## Postings analysed",
    ]
    assert md.count("Not enough evidence to suggest") == 3
    assert "Weak Sample: 0 Postings against a target of 30" in md
    assert not md.startswith(">")
    assert "Adzuna API" not in md


def test_replay_banner_only_on_replay_and_two_renders_are_identical():
    live = run_nodes(zero_state())["brief_markdown"]
    replayed = run_nodes(zero_state(), make_settings(replay_cache=Path("replay.sqlite")))
    assert replayed["brief"].replayed and replayed["brief_markdown"].startswith("> Replayed run:")
    assert run_nodes(zero_state())["brief_markdown"] == live


def test_run_notes_are_whole():
    first, second, last = plan("A"), plan("B"), plan("C")
    state = zero_state(
        questions=[
            ClarifyingQuestion(about=RequestField.role, text="Which role?", options=[], answer="Data Analyst"),
            ClarifyingQuestion(about=RequestField.location, text="Where?", options=[], answer=None),
        ],
        assumptions=[Assumption(about=RequestField.seniority, value="mid", reason="not stated")],
        focus=[Dimension.skills, Dimension.demand],
        search_plan=first, broadened_plans=[second, last],
        # The Caveats are out of alphabetical order on purpose: they must stay in log order.
        run_log=[
            note("collect", LogKind.note, "source totals", totals={"data analyst": {"adzuna": 99}}),
            note("stats", LogKind.caveat, "second caveat"),
            note("collect", LogKind.note, "source totals", totals={"data analyst": {"adzuna": 3200}, "analyst": {"usajobs": 7}}),
            note("stats", LogKind.caveat, "first caveat, kept in order"),
        ],
    )

    md = run_nodes(state)["brief_markdown"]
    notes = _run_notes(state)

    assert notes.final_plan == last and notes.earlier_plans == [first, second]
    assert notes.caveats == ["second caveat", "first caveat, kept in order"]
    assert notes.match_totals == [
        "Adzuna reported about 3,200 matches for data analyst. This is its own count, not a measure of demand.",
        "USAJOBS reported about 7 matches for analyst. This is its own count, not a measure of demand.",
    ]
    for text in ("Which role? → Data Analyst", "Where? → no answer", "seniority: mid (not stated)", "skills, demand"):
        assert text in md
    assert md.index("second caveat") < md.index("first caveat")


def test_match_totals_ignore_a_collect_note_without_totals():
    assert match_totals([note("collect", LogKind.note, "kept 3 Postings", kept=3)]) == []


def test_attribution_only_when_an_adzuna_posting_is_in_the_sample():
    def posting(source):
        return Posting(
            source=source, source_id="1", title="t", company=None, location="x", region=(), domain=None,
            posted_at=date(2026, 1, 1), closes_at=None, description="d", url="https://x", salary=None,
        )

    def notes(source):
        p = posting(source)
        return _run_notes(zero_state(postings={p.key: p}, sample=[p.key]))

    assert notes(Source.adzuna).attribution == "Jobs data provided by The Adzuna API"
    assert notes(Source.usajobs).attribution is None


def test_after_critic_goes_to_render_with_no_verdicts_and_the_router_is_registered():
    assert ROUTERS["critic"] is after_critic
    assert after_critic(zero_state()) == "render"
    assert after_critic(zero_state(critic_verdicts=[InsightVerdict(supported=False, p_yes=0.1)], revisions=2)) == "render"
    assert after_critic(zero_state(critic_verdicts=[InsightVerdict(supported=False, p_yes=0.1)])) == "write_brief"


def test_the_graph_uses_the_real_brief_nodes():
    graph = build_graph(dataclasses.replace(fake_deps(make_settings()), stub_stages=False), None)
    for name in ("write_brief", "critic", "render"):
        bound = graph.nodes[name].bound
        assert (bound.afunc or bound.func).__wrapped__.__module__ == "talent_scout.brief.nodes"


def test_a_run_on_stubs_with_the_real_brief_reaches_done_with_both_files(tmp_path, monkeypatch):
    settings = make_settings(runs_db=tmp_path / "runs.sqlite", runs_dir=tmp_path / "runs", gateway_db=tmp_path / "gw.sqlite")

    @asynccontextmanager
    async def open_deps(settings):
        yield fake_deps(settings)

    brief = make_nodes(fake_deps(settings))
    monkeypatch.setattr(controller_module, "open_deps", open_deps)
    monkeypatch.setattr(controller_module, "check_balance", pass_balance)
    monkeypatch.setattr(graph_module, "stub_nodes", lambda: {**stub_nodes(), **brief})
    monkeypatch.setattr(graph_module, "STUB_ROUTERS", {**STUB_ROUTERS, **ROUTERS})

    async def go():
        async with RunController.open(settings) as controller:
            handle = await controller.start("Engineer, Texas")
            while isinstance(terminal := await handle.wait(), Paused):
                handle = await controller.resume(handle.thread_id, ANSWER_FOR[terminal.pause.kind])
            return terminal, await controller.get_run(handle.thread_id)

    terminal, view = asyncio.run(go())

    assert view.record.status is RunStatus.done
    files = {p.name: p.read_text(encoding="utf-8") for p in terminal.paths}
    assert files["brief.md"].startswith("# Market Brief: Stub role, Stub city")
    assert '"No Relevant Postings were found' in files["brief.json"]
    logged = [(e.node, e.kind) for e in view.state.run_log if e.node in ("write_brief", "critic", "render")]
    assert logged == [("write_brief", LogKind.note), ("critic", LogKind.route), ("render", LogKind.note)]
