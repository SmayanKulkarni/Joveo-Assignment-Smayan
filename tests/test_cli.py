import asyncio

import aiosqlite
import pytest
from langgraph.graph import END

from talent_scout.clients import cli
from talent_scout.kernel.testing import make_settings
from talent_scout.kernel.types import Dimension
from talent_scout.runtime import controller as controller_module
from talent_scout.runtime import graph as graph_module
from talent_scout.runtime.controller import InvalidAnswer, RunController
from talent_scout.runtime.events import Paused
from talent_scout.runtime.guard import take_lock
from talent_scout.runtime.registry import Registry, RunStatus
from talent_scout.runtime.testing import (
    ANSWER_FOR,
    STUB_ROUTERS,
    open_fake_deps,
    pass_balance,
    stub_nodes,
)


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setattr(controller_module, "open_deps", open_fake_deps)
    monkeypatch.setattr(controller_module, "check_balance", pass_balance)
    s = make_settings(runs_db=tmp_path / "runs.sqlite", runs_dir=tmp_path / "runs", gateway_db=tmp_path / "gw.sqlite")
    monkeypatch.setattr(cli, "get_settings", lambda: s)
    return s


def type_replies(monkeypatch, *replies):
    """Script input(), and hand back the iterator so a test can check every reply was used."""
    remaining = iter(replies)
    monkeypatch.setattr("builtins.input", lambda _="": next(remaining))
    return remaining


# Answers that walk the stub path: clarify option 1, approve the plan, continue on low data.
WALK = ("1", "a", "c")


def only_run(settings) -> str:
    async def go():
        async with RunController.open(settings) as controller:
            return await controller.list_runs()

    (record,) = asyncio.run(go())
    return record.thread_id


def test_run_drives_the_stub_pauses_and_a_bad_answer_reasks_the_same_pause(settings, monkeypatch, capsys):
    real_resume, calls = cli.drive_resume, []

    async def refuse_first(settings, thread_id, answer):
        calls.append(answer)
        if len(calls) == 1:
            raise InvalidAnswer([{"loc": ("answers",), "msg": "nope"}])
        return await real_resume(settings, thread_id, answer)

    monkeypatch.setattr(cli, "drive_resume", refuse_first)
    # A wrong menu letter ("z") is re-asked too; the refused clarify answer is asked again.
    remaining = type_replies(monkeypatch, "1", "1", "z", "a", "c")

    assert cli.main(["run", "Engineer, Texas"]) == 0

    out = capsys.readouterr().out
    assert next(remaining, None) is None
    assert out.count("Clarifying questions") == 2
    assert "answers: nope" in out and "Pick one of the letters" in out
    assert "✓ render — stub" in out and "Stub brief" in out and "brief.md" in out
    assert calls[0] == calls[1] == {"answers": ["Stub role"]}


def test_resume_and_show_print_each_status(settings, monkeypatch, capsys):
    async def make_runs():
        ids = {}
        async with RunController.open(settings) as c:
            async def start(name, summary):
                handle = await c.start(summary)
                ids[name] = handle.thread_id
                return handle

            await (await start("paused", "paused one")).wait()

            handle = await start("done", "done one")
            while isinstance(terminal := await handle.wait(), Paused):
                handle = await c.resume(handle.thread_id, ANSWER_FOR[terminal.pause.kind])

        async def boom(state):
            raise ValueError("boom")

        with monkeypatch.context() as m:
            m.setattr(graph_module, "stub_nodes", lambda: {**stub_nodes(), "plan": boom})
            async with RunController.open(settings) as c:
                handle = await start("failed", "failed one")
                await handle.wait()
                await (await c.resume(ids["failed"], ANSWER_FOR["clarify"])).wait()

        with monkeypatch.context() as m:
            m.setattr(graph_module, "STUB_ROUTERS", {**STUB_ROUTERS, "clarity_check": lambda state: END})
            async with RunController.open(settings) as c:
                await (await start("aborted", "aborted one")).wait()
        return ids

    ids = asyncio.run(make_runs())

    def show(name, *flags):
        assert cli.main(["show", ids[name], *flags]) == 0
        return capsys.readouterr().out

    assert "Stub brief" in (done := show("done", "--log")) and "brief.md" in done and "Node" in done
    assert "Clarifying questions" in (paused := show("paused")) and f"scout resume {ids['paused']}" in paused
    assert f"Stopped at plan: ValueError: boom\nResume with `scout resume {ids['failed']}`" in show("failed")
    assert "Aborted: stub" in show("aborted")

    # A live task elsewhere: its row says running and it holds the lock, so reconcile leaves it alone.
    async def mark_running():
        async with aiosqlite.connect(settings.runs_db) as conn:
            await Registry(conn).transition(ids["paused"], RunStatus.running)

    asyncio.run(mark_running())
    held = take_lock(settings.runs_db, ids["paused"])
    assert cli.main(["resume", ids["paused"]]) == 1
    held.close()
    assert "This Run is open elsewhere" in capsys.readouterr().out

    # The failed Run's bug is fixed (the patch is gone), so resume retries it and walks on.
    type_replies(monkeypatch, "a", "c")
    assert cli.main(["resume", ids["failed"]]) == 0
    assert "Stopped at plan: ValueError: boom. Retrying." in capsys.readouterr().out

    type_replies(monkeypatch, *WALK)
    assert cli.main(["resume", ids["paused"]]) == 0
    assert "Clarifying questions" in capsys.readouterr().out

    assert cli.main(["resume", ids["done"]]) == 1
    assert f"Run already finished, see `scout show {ids['done']}`" in capsys.readouterr().out
    assert cli.main(["resume", "nosuch"]) == 1
    assert "UnknownRun: No Run nosuch" in capsys.readouterr().out


def test_resume_without_an_id_lists_resumable_runs_and_takes_the_first_on_enter(settings, monkeypatch, capsys):
    assert cli.main(["resume"]) == 0
    assert "No resumable Runs" in capsys.readouterr().out

    async def start_two():
        async with RunController.open(settings) as c:
            handles = [await c.start(name) for name in ("older", "newer")]
            for handle in handles:
                await handle.wait()
            return [h.thread_id for h in handles]

    older, newer = asyncio.run(start_two())
    # Enter picks the first row, the newest Run, then its clarify, plan and low-data answers.
    remaining = type_replies(monkeypatch, "", *WALK)

    assert cli.main(["resume"]) == 0

    out = capsys.readouterr().out
    assert next(remaining, None) is None
    assert older in out and newer in out and "clarify" in out
    assert asyncio.run(_status(settings, newer)) is RunStatus.done
    assert asyncio.run(_status(settings, older)) is RunStatus.paused


async def _status(settings, thread_id):
    async with RunController.open(settings) as controller:
        return (await controller.get_run(thread_id)).record.status


def test_focus_rejects_unknown_values_and_lands_in_the_checkpoint(settings, monkeypatch, capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["run", "Engineer, Texas", "--focus", "vibes"])
    assert exit_info.value.code == 2
    with pytest.raises(SystemExit):
        cli.main(["run", "   "])

    type_replies(monkeypatch, *WALK)
    # "salary" is the spec's alias for compensation.
    assert cli.main(["run", "Engineer, Texas", "--focus", "skills", "--focus", "salary"]) == 0

    thread_id = only_run(settings)

    async def focus():
        async with RunController.open(settings) as controller:
            return (await controller.get_run(thread_id)).state.focus

    assert asyncio.run(focus()) == [Dimension.skills, Dimension.compensation]


def test_edit_reopens_the_editor_with_the_error_on_top_until_the_plan_validates(monkeypatch):
    plan = cli.SearchPlan(
        titles=["Stub role"], country="us", location="Stub city", radius_km=0,
        max_days_old=30, target_postings=20, category=None,
    )
    seen = []

    def fake_editor(path):
        text = path.read_text(encoding="utf-8")
        seen.append(text)
        if len(seen) == 1:
            path.write_text(text.replace('"Stub role"', ""), encoding="utf-8")  # breaks the JSON
        else:
            path.write_text(plan.model_copy(update={"radius_km": 25}).model_dump_json(), encoding="utf-8")

    monkeypatch.setattr(cli, "_open_editor", fake_editor)

    edited = cli.edit_plan(plan)

    assert edited.radius_km == 25
    assert not seen[0].startswith("//") and seen[1].startswith("// ")
