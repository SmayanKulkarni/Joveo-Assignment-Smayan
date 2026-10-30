import asyncio
import json

import aiosqlite
import pytest

from talent_scout.kernel.llm import BalanceTooLow
from talent_scout.kernel.testing import make_settings
from talent_scout.kernel.types import Dimension
from talent_scout.runtime import controller as controller_module
from talent_scout.runtime import graph as graph_module
from talent_scout.runtime.controller import InvalidAnswer, NotResumable, RunController, UnknownRun
from talent_scout.runtime.events import Done, NodeDone, Paused, Stopped
from talent_scout.runtime.guard import RunLocked, take_lock
from talent_scout.runtime.pause import ClarifyPause, LowDataPause, PlanReviewPause
from talent_scout.runtime.registry import Registry, RunStatus
from talent_scout.runtime.testing import ANSWER_FOR, open_fake_deps, pass_balance, stub_nodes


async def too_low(_):
    raise BalanceTooLow("empty")


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setattr(controller_module, "open_deps", open_fake_deps)
    monkeypatch.setattr(controller_module, "check_balance", pass_balance)
    return make_settings(runs_db=tmp_path / "runs.sqlite", runs_dir=tmp_path / "runs", gateway_db=tmp_path / "gw.sqlite")


def patch_node(monkeypatch, name, fn):
    monkeypatch.setattr(graph_module, "stub_nodes", lambda: {**stub_nodes(), name: fn})


def raises_once(monkeypatch, name):
    """Make a stub raise on its first call, then behave."""
    real = stub_nodes()[name]
    calls = []

    async def node(state):
        calls.append(name)
        if len(calls) == 1:
            raise ValueError("boom")
        return await real(state)

    patch_node(monkeypatch, name, node)
    return calls


async def to_terminal(controller, handle):
    """Answer every Pause until the Run stops or finishes."""
    while isinstance(terminal := await handle.wait(), Paused):
        handle = await controller.resume(handle.thread_id, ANSWER_FOR[terminal.pause.kind])
    return handle, terminal


async def set_row_running(settings, thread_id):
    # As a kill would leave it: the checkpoint moved on, but the row was never updated.
    async with aiosqlite.connect(settings.runs_db) as conn:
        await Registry(conn).transition(thread_id, RunStatus.running)


def test_happy_path_goes_through_each_typed_pause_to_done(settings):
    async def go():
        async with RunController.open(settings) as controller:
            handle = await controller.start("Engineer, Texas", [Dimension.skills])
            pauses = []
            while isinstance(terminal := await handle.wait(), Paused):
                pauses.append(await controller.get_pause(handle.thread_id))
                assert terminal.pause == pauses[-1]
                assert (await controller.get_run(handle.thread_id)).record.status is RunStatus.paused
                handle = await controller.resume(handle.thread_id, ANSWER_FOR[terminal.pause.kind])
            view = await controller.get_run(handle.thread_id)
            return pauses, terminal, view, [e async for e in handle.events()]

    pauses, terminal, view, events = asyncio.run(go())

    assert [type(p) for p in pauses] == [ClarifyPause, PlanReviewPause, LowDataPause]
    assert view.record.status is RunStatus.done
    assert view.pause is None
    assert view.state.focus == [Dimension.skills]
    assert view.record.summary == "Engineer, Texas"
    assert isinstance(terminal, Done) and terminal.status == "done"
    # The last leg, replayed from the buffer, in order and ending on the terminal event.
    assert [e.node for e in events if isinstance(e, NodeDone)] == ["low_data_review", "stats", "write_brief", "critic", "render"]
    assert events[0] == NodeDone(node="low_data_review", notes=["continue"])
    assert events[-1] == terminal


def test_done_writes_both_brief_files_and_reconcile_writes_them_too(settings):
    async def go():
        async with RunController.open(settings) as controller:
            handle = await controller.start("Engineer, Texas")
            _, terminal = await to_terminal(controller, handle)
            first = {p.name: p.read_text() for p in terminal.paths}

            for path in terminal.paths:
                path.unlink()
            await set_row_running(settings, handle.thread_id)
            view = await controller.get_run(handle.thread_id)
            return first, terminal, view

    first, terminal, view = asyncio.run(go())

    assert set(first) == {"brief.json", "brief.md"}
    assert json.loads(first["brief.json"]) is not None
    assert first["brief.md"] == "# Stub brief"
    assert view.record.status is RunStatus.done
    assert all(path.exists() for path in terminal.paths)


def test_unknown_run_is_refused(settings):
    async def go():
        async with RunController.open(settings) as controller:
            for call in (controller.resume, controller.get_pause, controller.get_run):
                with pytest.raises(UnknownRun):
                    await call("nope")
            assert await controller.list_runs() == []

    asyncio.run(go())


def test_refusals_change_nothing(settings, monkeypatch):
    async def go():
        async with RunController.open(settings) as controller:
            handle = await controller.start("Engineer, Texas")
            await handle.wait()
            thread_id = handle.thread_id
            before = await controller.get_run(thread_id)

            with pytest.raises(InvalidAnswer):
                await controller.resume(thread_id, {"answers": "not a list"})
            with pytest.raises(InvalidAnswer):
                await controller.resume(thread_id, None)

            lock = take_lock(settings.runs_db, thread_id)
            with pytest.raises(RunLocked):
                await controller.resume(thread_id, ANSWER_FOR["clarify"])
            lock.close()

            monkeypatch.setattr(controller_module, "check_balance", too_low)
            with pytest.raises(BalanceTooLow):
                await controller.resume(thread_id, ANSWER_FOR["clarify"])
            with pytest.raises(BalanceTooLow):
                await controller.start("Another")
            assert len(await controller.list_runs()) == 1
            assert await controller.get_run(thread_id) == before

            # Nothing kept the lock: the same answer now goes through.
            monkeypatch.setattr(controller_module, "check_balance", pass_balance)
            handle = await controller.resume(thread_id, ANSWER_FOR["clarify"])
            await handle.wait()

    asyncio.run(go())


def test_a_finished_run_is_not_resumable(settings):
    async def go():
        async with RunController.open(settings) as controller:
            handle, _ = await to_terminal(controller, await controller.start("Engineer, Texas"))
            before = await controller.get_run(handle.thread_id)
            with pytest.raises(NotResumable) as refused:
                await controller.resume(handle.thread_id)
            assert refused.value.status is RunStatus.done
            assert await controller.get_run(handle.thread_id) == before

    asyncio.run(go())


def test_balance_check_is_skipped_with_a_replay_cache(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(controller_module, "check_balance", too_low)
    replaying = settings.model_copy(update={"replay_cache": tmp_path / "replay.sqlite"})

    async def go():
        async with RunController.open(replaying) as controller:
            handle = await controller.start("Engineer, Texas")
            await handle.wait()
            resumed = await controller.resume(handle.thread_id, ANSWER_FOR["clarify"])
            return await resumed.wait()

    assert isinstance(asyncio.run(go()), Paused)


def test_raising_node_gives_failed_and_stopped_and_resume_reruns_only_it(settings, monkeypatch):
    calls = raises_once(monkeypatch, "fetch_agent")

    async def go():
        async with RunController.open(settings) as controller:
            handle, stopped = await to_terminal(controller, await controller.start("Engineer, Texas"))
            failed = await controller.get_run(handle.thread_id)

            with pytest.raises(InvalidAnswer):
                await controller.resume(handle.thread_id, {"action": "continue"})

            resumed = await controller.resume(handle.thread_id)
            paused = await resumed.wait()
            events = [e async for e in resumed.events()]
            return stopped, failed, paused, events, await controller.get_run(handle.thread_id)

    stopped, failed, paused, events, after = asyncio.run(go())

    assert stopped == Stopped(node="fetch_agent", reason="ValueError: boom")
    assert failed.record.status is RunStatus.failed
    assert failed.record.error == "ValueError: boom"
    assert failed.stopped_at == "fetch_agent"
    assert isinstance(paused.pause, LowDataPause)
    assert calls == ["fetch_agent", "fetch_agent"]
    assert [e.node for e in events if isinstance(e, NodeDone)] == ["fetch_agent", "collect", "relevance"]
    # Nothing before the failed node ran twice.
    assert [e.node for e in after.state.run_log].count("plan") == 1
    assert (after.record.status, after.record.error) == (RunStatus.paused, None)


def test_cancel_gives_a_resumable_failed_run_while_a_live_row_stays_running(settings, monkeypatch):
    entered = asyncio.Event()
    real = stub_nodes()["fetch_agent"]
    calls = []

    async def blocks_once(state):
        calls.append(1)
        if len(calls) == 1:
            entered.set()
            await asyncio.sleep(3600)
        return await real(state)

    patch_node(monkeypatch, "fetch_agent", blocks_once)

    async def go():
        async with RunController.open(settings) as controller:
            handle = await controller.start("Engineer, Texas")
            await handle.wait()
            handle = await controller.resume(handle.thread_id, ANSWER_FOR["clarify"])
            await handle.wait()
            handle = await controller.resume(handle.thread_id, ANSWER_FOR["plan_review"])
            await entered.wait()

            # A read must not mistake a live task's row for a stale one.
            assert (await controller.get_run(handle.thread_id)).record.status is RunStatus.running
            assert (await controller.list_runs())[0].status is RunStatus.running

            stopped = await handle.cancel()
            cancelled = await controller.get_run(handle.thread_id)
            resumed = await controller.resume(handle.thread_id)
            return stopped, cancelled, await handle.wait(), await resumed.wait()

    stopped, cancelled, waited, paused = asyncio.run(go())

    assert stopped == Stopped(node="fetch_agent", reason="cancelled")
    assert waited == stopped
    assert (cancelled.record.status, cancelled.record.error) == (RunStatus.failed, "cancelled")
    assert cancelled.stopped_at == "fetch_agent"
    assert isinstance(paused.pause, LowDataPause)


def test_cancel_before_the_first_checkpoint_aborts_and_frees_the_lock(settings):
    async def go():
        async with RunController.open(settings) as controller:
            handle = await controller.start("Engineer, Texas")
            first, second = await asyncio.gather(handle.cancel(), handle.cancel())
            view = await controller.get_run(handle.thread_id)
            take_lock(settings.runs_db, handle.thread_id).close()
            with pytest.raises(NotResumable):
                await controller.resume(handle.thread_id)
            return first, second, view

    first, second, view = asyncio.run(go())

    assert first == second == Stopped(node=None, reason="cancelled")
    assert (view.record.status, view.record.error) == (RunStatus.aborted, "cancelled")
    assert view.state is None


def test_cancel_after_a_pause_leaves_the_run_paused(settings):
    async def go():
        async with RunController.open(settings) as controller:
            handle = await controller.start("Engineer, Texas")
            await handle.wait()
            await handle.cancel()
            return (await controller.get_run(handle.thread_id)).record.status

    assert asyncio.run(go()) is RunStatus.paused


def test_stale_running_row_reconciles_on_read(settings):
    async def go():
        async with RunController.open(settings) as controller:
            handle = await controller.start("Engineer, Texas")
            await handle.wait()
            await set_row_running(settings, handle.thread_id)
            view = await controller.get_run(handle.thread_id)

            await set_row_running(settings, handle.thread_id)
            listed = await controller.list_runs(resumable_only=True)
            return view, listed

    view, listed = asyncio.run(go())

    assert view.record.status is RunStatus.paused
    assert [r.status for r in listed] == [RunStatus.paused]


def test_list_runs_is_newest_first_and_filters_resumable(settings):
    async def go():
        async with RunController.open(settings) as controller:
            finished, _ = await to_terminal(controller, await controller.start("first"))
            paused = await controller.start("second")
            await paused.wait()
            return (
                finished.thread_id, paused.thread_id,
                [r.thread_id for r in await controller.list_runs()],
                [r.thread_id for r in await controller.list_runs(resumable_only=True)],
            )

    finished, paused, everything, resumable = asyncio.run(go())

    assert everything == [paused, finished]
    assert resumable == [paused]


def test_closing_a_subscriber_does_not_stop_the_run(settings):
    async def go():
        async with RunController.open(settings) as controller:
            handle = await controller.start("Engineer, Texas")
            live = handle.events()
            first = await anext(live)
            await live.aclose()
            return first, await handle.wait()

    first, terminal = asyncio.run(go())

    assert first == NodeDone(node="intake", notes=["stub"])
    assert isinstance(terminal, Paused)


def test_a_live_subscriber_sees_what_a_late_one_replays(settings):
    async def go():
        async with RunController.open(settings) as controller:
            handle = await controller.start("Engineer, Texas")
            live = [e async for e in handle.events()]
            return live, [e async for e in handle.events()]

    live, replayed = asyncio.run(go())

    assert live == replayed
    assert [e.node for e in live[:-1]] == ["intake", "clarity_check"]
    assert isinstance(live[-1], Paused)


def test_open_builds_the_real_deps_without_a_network_call(tmp_path):
    # Only opens and closes: this is the wiring the fakes replace everywhere else.
    settings = make_settings(runs_db=tmp_path / "runs.sqlite", gateway_db=tmp_path / "gw.sqlite")

    async def go():
        async with RunController.open(settings) as controller:
            return await controller.list_runs()

    assert asyncio.run(go()) == []
