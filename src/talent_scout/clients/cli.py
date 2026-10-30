import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import ValidationError
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text

from talent_scout.clients.pauses import render_pause
from talent_scout.kernel.llm import BalanceTooLow
from talent_scout.kernel.settings import Settings, get_settings
from talent_scout.kernel.types import Dimension, SearchPlan
from talent_scout.request_plan.types import PlanAction
from talent_scout.runtime.controller import (
    InvalidAnswer,
    NotResumable,
    RunController,
    RunHandle,
    RunView,
    UnknownRun,
)
from talent_scout.runtime.events import NodeDone, Paused, RunEvent, Stopped
from talent_scout.runtime.guard import RunLocked
from talent_scout.runtime.registry import RunStatus

SIGINT_EXIT = 130
# "salary" is the spec's name for compensation.
FOCUS_CHOICES = [*(d.value for d in Dimension), "salary"]
PLAN_CHOICES = {"a": PlanAction.approve, "e": PlanAction.edit, "r": PlanAction.reject, "x": PlanAction.abort}
LOW_DATA_CHOICES = {"b": "broaden", "c": "continue", "x": "abort"}
REFUSALS = (BalanceTooLow, RunLocked, UnknownRun, NotResumable, httpx.HTTPError)

console = Console()


async def _follow(handle: RunHandle) -> RunEvent:
    try:
        async for event in handle.events():
            if isinstance(event, NodeDone):
                print(f"✓ {event.node} — {'; '.join(event.notes)}" if event.notes else f"✓ {event.node}")
        return await handle.wait()
    except asyncio.CancelledError:
        # Ctrl-C: asyncio.run cancelled this driver, and the Run is stopped here so it stays resumable.
        stopped = await handle.cancel()
        print(_stopped_line(stopped, handle.thread_id))
        raise


async def drive_start(settings: Settings, request: str, focus: list[Dimension]) -> tuple[str, RunEvent]:
    async with RunController.open(settings) as controller:
        handle = await controller.start(request, focus)
        return handle.thread_id, await _follow(handle)


async def drive_resume(settings: Settings, thread_id: str, answer: dict | None) -> RunEvent:
    async with RunController.open(settings) as controller:
        return await _follow(await controller.resume(thread_id, answer))


async def _get_view(settings: Settings, thread_id: str) -> RunView:
    async with RunController.open(settings) as controller:
        return await controller.get_run(thread_id)


async def _resumable_views(settings: Settings) -> list[RunView]:
    async with RunController.open(settings) as controller:
        return [await controller.get_run(r.thread_id) for r in await controller.list_runs(resumable_only=True)]


def _choose(choices: dict) -> object:
    menu = "  ".join(f"[{key}] {value}" for key, value in choices.items())
    while (key := input(f"{menu}\n> ").strip().lower()) not in choices:
        print("Pick one of the letters shown.")
    return choices[key]


def _ask_question(number: int, question) -> str:
    reply = input(f"Answer {number} (option number, free text, or Enter to skip): ").strip()
    if reply.isdigit() and 1 <= int(reply) <= len(question.options):
        return question.options[int(reply) - 1]
    return reply


def _open_editor(path: Path) -> None:
    subprocess.run(f'{os.environ.get("EDITOR", "notepad")} "{path}"', shell=True, check=True)


def edit_plan(plan: SearchPlan) -> SearchPlan:
    body, error = plan.model_dump_json(indent=2), None
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "search_plan.json"
        while True:
            banner = "".join(f"// {line}\n" for line in error.splitlines()) if error else ""
            path.write_text(banner + body, encoding="utf-8")
            _open_editor(path)
            # JSON has no comments, so the error banner is dropped before parsing.
            lines = path.read_text(encoding="utf-8-sig").splitlines(keepends=True)
            body = "".join(line for line in lines if not line.startswith("//"))
            try:
                return SearchPlan.model_validate_json(body)
            except ValidationError as e:
                error = "\n".join(f"{'.'.join(map(str, err['loc'])) or 'plan'}: {err['msg']}" for err in e.errors())


def _ask_plan_review(plan: SearchPlan) -> dict:
    while True:
        action = _choose(PLAN_CHOICES)
        if action is PlanAction.edit:
            try:
                return {"action": action, "plan": edit_plan(plan).model_dump(mode="json"), "feedback": None}
            except subprocess.CalledProcessError:
                print("The editor failed.")
                continue
        feedback = None
        if action is PlanAction.reject:
            feedback = input("What should change? ").strip() or None
        return {"action": action, "plan": None, "feedback": feedback}


def prompt(pause) -> dict:
    print(render_pause(pause))
    match pause.kind:
        case "clarify":
            return {"answers": [_ask_question(n, q) for n, q in enumerate(pause.payload.questions, 1)]}
        case "plan_review":
            return _ask_plan_review(pause.payload.plan)
        case "low_data_review":
            return {"action": _choose(LOW_DATA_CHOICES)}


def _ago(moment: datetime) -> str:
    seconds = int((datetime.now(UTC) - moment).total_seconds())
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= size:
            return f"{seconds // size}{unit} ago"
    return f"{seconds}s ago"


def _table(columns: list[str], rows: list[list[str]]) -> Table:
    table = Table(*columns)
    for row in rows:
        # Text, so a "[...]" in a request or log message isn't read as rich markup.
        table.add_row(*(Text(cell) for cell in row))
    return table


def _stopped_line(stopped: Stopped, thread_id: str) -> str:
    if stopped.node is None:  # before the first checkpoint there is nothing to resume
        return f"Stopped: {stopped.reason}."
    return f"Stopped at {stopped.node}: {stopped.reason}. Resume with `scout resume {thread_id}`"


def _print_errors(error: InvalidAnswer) -> None:
    print("That answer was not accepted:")
    for item in error.errors:
        where = ".".join(map(str, item.get("loc", ())))
        print(f"  - {where + ': ' if where else ''}{item['msg']}")


def _finish(thread_id: str, outcome: RunEvent) -> int:
    if isinstance(outcome, Stopped):
        print(_stopped_line(outcome, thread_id))
        return 1
    if outcome.status == "aborted":
        print(f"Run aborted, see `scout show {thread_id}`")
        return 0
    markdown_path = next(p for p in outcome.paths if p.suffix == ".md")
    console.print(Markdown(markdown_path.read_text(encoding="utf-8")))
    print("Files:", *outcome.paths, sep="\n  ")
    return 0


def _converse(settings: Settings, thread_id: str, outcome: RunEvent) -> int:
    while isinstance(outcome, Paused):
        try:
            answer = prompt(outcome.pause)
        except KeyboardInterrupt:
            print(f"\nResume with `scout resume {thread_id}`")
            return SIGINT_EXIT
        try:
            outcome = asyncio.run(drive_resume(settings, thread_id, answer))
        except InvalidAnswer as e:
            _print_errors(e)  # nothing changed, so the same Pause is asked again
    return _finish(thread_id, outcome)


def _run(args) -> int:
    settings = get_settings()
    focus = [Dimension("compensation" if f == "salary" else f) for f in args.focus]
    thread_id, outcome = asyncio.run(drive_start(settings, args.request, focus))
    return _converse(settings, thread_id, outcome)


def _pick_run(settings: Settings) -> str | None:
    views = asyncio.run(_resumable_views(settings))
    if not views:
        print("No resumable Runs")
        return None
    rows = [
        [str(n), v.record.thread_id, v.record.status, v.record.summary, _ago(v.record.updated_at),
         v.pause.kind if v.pause else v.stopped_at or ""]
        for n, v in enumerate(views, 1)
    ]
    console.print(_table(["#", "Run", "Status", "Summary", "Updated", "Hint"], rows))
    ids = {v.record.thread_id for v in views}
    while True:
        choice = input("Run number or ID [1]: ").strip() or "1"
        if choice.isdigit() and 1 <= int(choice) <= len(views):
            return views[int(choice) - 1].record.thread_id
        if choice in ids:
            return choice
        print("Not one of the Runs listed.")


def _resume(args) -> int:
    settings = get_settings()
    thread_id = args.thread_id or _pick_run(settings)
    if thread_id is None:
        return 0
    view = asyncio.run(_get_view(settings, thread_id))
    match view.record.status:
        case RunStatus.paused:
            return _converse(settings, thread_id, Paused(pause=view.pause))
        case RunStatus.failed:
            print(f"Stopped at {view.stopped_at}: {view.record.error}. Retrying.")
            return _converse(settings, thread_id, asyncio.run(drive_resume(settings, thread_id, None)))
        case RunStatus.running:  # reconcile ran in get_run, so a running row means a live task
            raise RunLocked(thread_id)
        case _:
            print(f"Run already finished, see `scout show {thread_id}`")
            return 1


def _show(args) -> int:
    settings = get_settings()
    view = asyncio.run(_get_view(settings, args.thread_id))
    record, state = view.record, view.state
    resume_hint = f"Resume with `scout resume {record.thread_id}`"
    print(f"Run {record.thread_id} · {record.status} · updated {_ago(record.updated_at)}\n{record.summary}\n")
    match record.status:
        case RunStatus.done:
            console.print(Markdown(state.brief_markdown or ""))
            print(f"File: {settings.runs_dir / record.thread_id / 'brief.md'}")
        case RunStatus.paused:
            print(render_pause(view.pause))
            print(resume_hint)
        case RunStatus.failed:
            print(f"Stopped at {view.stopped_at}: {record.error}\n{resume_hint}")
        case RunStatus.aborted:
            reason = state.run_log[-1].message if state and state.run_log else record.error
            print(f"Aborted: {reason}" if reason else "Aborted")
    if args.log:
        console.print(_table(["Node", "Kind", "Message"], [[e.node, e.kind, e.message] for e in state.run_log] if state else []))
    return 0


def _request(text: str) -> str:
    if not text.strip():
        raise argparse.ArgumentTypeError("the request can't be blank")
    return text.strip()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scout")
    commands = parser.add_subparsers(required=True)

    run = commands.add_parser("run", help="start a Run")
    run.add_argument("request", type=_request)
    run.add_argument("--focus", action="append", choices=FOCUS_CHOICES, default=[], help="repeat for several")
    run.set_defaults(command=_run)

    resume = commands.add_parser("resume", help="pick up a paused or stopped Run")
    resume.add_argument("thread_id", nargs="?")
    resume.set_defaults(command=_resume)

    show = commands.add_parser("show", help="read a Run without touching it")
    show.add_argument("thread_id")
    show.add_argument("--log", action="store_true", help="also print the run log")
    show.set_defaults(command=_show)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    # Piped output on Windows is cp1252, which can't encode "✓" and would crash a paid Run mid-way.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        return args.command(args)
    except KeyboardInterrupt:
        return SIGINT_EXIT
    except REFUSALS as e:
        # An HTTPError can have an empty message, so the class name goes first.
        print("This Run is open elsewhere" if isinstance(e, RunLocked) else f"{type(e).__name__}: {e}")
        return 1
