import asyncio
import json
import subprocess
import sys
from pathlib import Path

from talent_scout.kernel.testing import make_settings
from talent_scout.runtime import controller as controller_module
from talent_scout.runtime.controller import RunController
from talent_scout.runtime.registry import RunStatus
from talent_scout.runtime.testing import open_fake_deps, pass_balance

# One Controller in its own process. Prints one JSON line per step, then stays alive at a Pause
# or inside a blocked node, so the parent can kill it there.
WORKER = """
import asyncio, json, sys
from pathlib import Path

from talent_scout.kernel.testing import make_settings
from talent_scout.kernel.types import RequestField
from talent_scout.runtime import controller as c, graph
from talent_scout.runtime.events import Done, Paused
from talent_scout.runtime.guard import RunLocked
from talent_scout.runtime.pause import ClarifyPause
from talent_scout.runtime.testing import ANSWER_FOR, open_fake_deps, pass_balance, stub_nodes

c.open_deps, c.check_balance = open_fake_deps, pass_balance


def say(**fields):
    print(json.dumps(fields), flush=True)


async def block(state):
    await asyncio.sleep(3600)


async def main(root, command, thread_id):
    settings = make_settings(runs_db=root / "runs.sqlite", runs_dir=root / "runs")
    if command == "block":
        graph.stub_nodes = lambda: {**stub_nodes(), "intake": block}
    async with c.RunController.open(settings) as controller:
        if command == "block":
            handle = await controller.start("Engineer, Texas")
            say(thread_id=handle.thread_id)
            await handle.wait()
            return
        if command == "start":
            handle = await controller.start("Engineer, Texas")
        else:
            pause = await controller.get_pause(thread_id)
            typed = None
            if isinstance(pause, ClarifyPause):
                typed = isinstance(pause.payload.questions[0].about, RequestField)
            say(pause=type(pause).__name__, typed_enum=typed)
            try:
                handle = await controller.resume(thread_id, ANSWER_FOR[pause.kind] if pause else None)
            except RunLocked:
                say(refused="RunLocked")
                return
        terminal = await handle.wait()
        if isinstance(terminal, Paused):
            say(thread_id=handle.thread_id, paused=terminal.pause.kind)
            sys.stdin.read()
        else:
            say(thread_id=handle.thread_id, status=terminal.status, paths=[str(p) for p in terminal.paths])


asyncio.run(main(Path(sys.argv[1]), sys.argv[2], sys.argv[3]))
"""


def spawn(root: Path, command: str, thread_id: str = "") -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-c", WORKER, str(root), command, thread_id],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )


def read(process: subprocess.Popen) -> dict:
    line = process.stdout.readline()
    assert line, "the worker exited without reporting"
    return json.loads(line)


def hard_kill(process: subprocess.Popen) -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/PID", str(process.pid)], check=True, capture_output=True)
    else:
        process.kill()
    process.wait(timeout=30)
    process.stdout.close()
    process.stdin.close()


def finish(process: subprocess.Popen) -> None:
    assert process.wait(timeout=60) == 0
    process.stdout.close()
    process.stdin.close()


def status_of(root: Path, thread_id: str, monkeypatch) -> RunStatus:
    monkeypatch.setattr(controller_module, "open_deps", open_fake_deps)
    monkeypatch.setattr(controller_module, "check_balance", pass_balance)
    settings = make_settings(runs_db=root / "runs.sqlite", runs_dir=root / "runs")

    async def go():
        async with RunController.open(settings) as controller:
            return (await controller.get_run(thread_id)).record.status

    return asyncio.run(go())


def test_a_run_killed_at_every_pause_resumes_in_a_fresh_process_to_done(tmp_path, monkeypatch):
    first = spawn(tmp_path, "start")
    report = read(first)
    thread_id = report["thread_id"]
    assert report["paused"] == "clarify"
    hard_kill(first)

    second = spawn(tmp_path, "resume", thread_id)
    # This settles the StrEnum question: an enum nested in a payload comes back typed in a fresh process.
    assert read(second) == {"pause": "ClarifyPause", "typed_enum": True}
    assert read(second)["paused"] == "plan_review"
    hard_kill(second)

    third = spawn(tmp_path, "resume", thread_id)
    assert read(third)["pause"] == "PlanReviewPause"
    assert read(third)["paused"] == "low_data_review"
    hard_kill(third)

    fourth = spawn(tmp_path, "resume", thread_id)
    assert read(fourth)["pause"] == "LowDataPause"
    done = read(fourth)
    finish(fourth)

    assert done["status"] == "done"
    assert {Path(p).name for p in done["paths"]} == {"brief.json", "brief.md"}
    assert all(Path(p).exists() for p in done["paths"])
    assert status_of(tmp_path, thread_id, monkeypatch) is RunStatus.done


def test_a_second_process_gets_run_locked_and_a_kill_frees_the_run(tmp_path, monkeypatch):
    holder = spawn(tmp_path, "block")
    thread_id = read(holder)["thread_id"]
    try:
        second = spawn(tmp_path, "resume", thread_id)
        read(second)  # the get_pause report, which takes no lock
        assert read(second) == {"refused": "RunLocked"}
        finish(second)
    finally:
        hard_kill(holder)

    # Killed mid-node: the row is stale, and a resume reruns that node from its input checkpoint.
    fresh = spawn(tmp_path, "resume", thread_id)
    assert read(fresh)["pause"] == "NoneType"
    assert read(fresh)["paused"] == "clarify"
    hard_kill(fresh)
