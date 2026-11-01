import asyncio
import logging

import pytest

from talent_scout.kernel.testing import make_settings
from talent_scout.runtime.controller import RunController
from talent_scout.runtime.demo import POSTINGS
from talent_scout.runtime.events import (
    ApiCalled, Done, ExtractProgress, NodeStarted, Paused, Reasoning, Stopped, Token, ToolCalled, ToolReturned,
)
from talent_scout.runtime.graph import OWNERS, graph_topology

PLAN = {
    "titles": ["Data Engineer"], "country": "us", "location": "Austin, Texas", "radius_km": 10,
    "max_days_old": 30, "target_postings": 20, "category": None,
}
APPROVE = {"action": "approve", "plan": None, "feedback": None}
REJECT = {"action": "reject", "plan": None, "feedback": "wider"}
EDIT = {"action": "edit", "plan": PLAN, "feedback": None}
ABORT = {"action": "abort", "plan": None, "feedback": None}
CLARIFY = {"answers": ["Austin, Texas"]}


def low(action):
    return {"action": action, "guidance": None}


@pytest.fixture
def settings(tmp_path):
    return make_settings(demo=True, demo_delay=0, runs_db=tmp_path / "runs.sqlite", runs_dir=tmp_path / "runs")


async def drive(controller, request, plan_review, low_data):
    """Answer each Pause from the lists given, and return every event of the Run, in order."""
    answers = {"clarify": [CLARIFY], "plan_review": list(plan_review), "low_data_review": list(low_data)}
    events = []

    async def watch(handle):
        async for event in handle.events():
            events.append(event)

    handle = await controller.start(request)
    while True:
        watcher = asyncio.create_task(watch(handle))
        terminal = await handle.wait()
        await watcher
        if not isinstance(terminal, Paused):
            return handle.thread_id, events
        handle = await controller.resume(handle.thread_id, answers[terminal.pause.kind].pop(0))


def run_demo(settings, request="Data Engineer", plan_review=(APPROVE,), low_data=(low("broaden"),)):
    async def go():
        async with RunController.open(settings) as controller:
            thread_id, events = await drive(controller, request, plan_review, low_data)
            return events, await controller.get_run(thread_id)

    return asyncio.run(go())


def test_demo_run_emits_every_event_type_through_all_pauses(settings, caplog):
    with caplog.at_level(logging.WARNING):
        events, view = run_demo(settings, plan_review=(REJECT, EDIT))

    kinds = {type(e) for e in events}
    assert {Token, Reasoning, ToolCalled, ToolReturned, ApiCalled, ExtractProgress, Paused, Done} <= kinds
    assert [e.pause.kind for e in events if isinstance(e, Paused)] == ["clarify", "plan_review", "plan_review", "low_data_review"]
    assert any(e.cached for e in events if isinstance(e, ApiCalled)) and any(not e.cached for e in events if isinstance(e, ApiCalled))
    # The critic hands back to write_brief once.
    assert [e.node for e in events if isinstance(e, NodeStarted)].count("write_brief") == 2
    assert view.record.status == "done"
    assert "Blocked deserialization" not in caplog.text
    paths = {p.name: p for p in settings.runs_dir.glob(f"{view.record.thread_id}/*")}
    assert "# Market Brief: Data Engineer" in paths["brief.md"].read_text(encoding="utf-8")


def test_broaden_finds_all_postings_and_continue_keeps_the_first_three(settings, tmp_path):
    events, broadened = run_demo(settings)
    assert len(broadened.state.sample) == len(POSTINGS)
    assert [e.total for e in events if isinstance(e, ExtractProgress)][-1] == len(POSTINGS)

    other = make_settings(demo=True, demo_delay=0, runs_db=tmp_path / "b.sqlite", runs_dir=tmp_path / "b")
    _, continued = run_demo(other, low_data=(low("continue"),))
    assert len(continued.state.sample) == 3


@pytest.mark.parametrize("plan_review, low_data", [((ABORT,), ()), ((APPROVE,), (low("abort"),))])
def test_abort_ends_the_run_without_a_brief(settings, plan_review, low_data):
    events, view = run_demo(settings, plan_review=plan_review, low_data=low_data)
    assert view.record.status == "aborted" and view.state.brief is None
    assert isinstance(events[-1], Done) and events[-1].status == "aborted"


def test_fail_stops_once_in_normalise_skills_and_resume_reaches_done(settings):
    async def go():
        async with RunController.open(settings) as controller:
            handle = await controller.start("fail please")
            answers = {"clarify": CLARIFY, "plan_review": APPROVE, "low_data_review": low("broaden")}
            while isinstance(terminal := await handle.wait(), Paused):
                handle = await controller.resume(handle.thread_id, answers[terminal.pause.kind])
            assert isinstance(terminal, Stopped) and terminal.node == "normalise_skills"
            assert controller.attached(handle.thread_id) is None
            logged = len((await controller.get_run(handle.thread_id)).state.run_log)
            resumed = await controller.resume(handle.thread_id)
            # A resume's handle starts after the log the first leg wrote.
            assert resumed.log_start == logged > 0
            assert controller.attached(handle.thread_id) is resumed
            done = await resumed.wait()
            return done, (await controller.get_run(handle.thread_id)).record.status

    done, status = asyncio.run(go())
    assert isinstance(done, Done) and status == "done"


def test_graph_topology_lists_nodes_in_owner_order():
    topology = graph_topology()
    assert [n["id"] for n in topology["nodes"]] == [n for nodes in OWNERS.values() for n in nodes]
    assert {"source": "critic", "target": "write_brief"} in topology["edges"]
