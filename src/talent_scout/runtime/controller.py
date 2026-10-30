import asyncio
import logging
import sqlite3
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import aiosqlite
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import ValidationError

from talent_scout.gateway.gateway import make_gateway
from talent_scout.kernel.jev import make_jev
from talent_scout.kernel.llm import check_balance, make_tiers
from talent_scout.kernel.settings import Settings
from talent_scout.kernel.state import State
from talent_scout.kernel.types import Dimension, Model
from talent_scout.runtime.deps import Deps
from talent_scout.runtime.events import LIVE_ONLY, ChunkMapper, Done, Paused, RunEvent, Stopped
from talent_scout.runtime.graph import build_graph
from talent_scout.runtime.guard import RunLocked, take_lock
from talent_scout.runtime.pause import ALLOWED_MSGPACK, ANSWERS, Pause
from talent_scout.runtime.registry import RESUMABLE, Registry, RunRecord, RunStatus, derive_status

logger = logging.getLogger(__name__)

STREAM_MODES = ["updates", "messages", "custom", "tasks"]
BUFFER_SIZE = 5000
SETUP_ATTEMPTS = 5
BUSY_TIMEOUT_S = 5
ERROR_CHARS = 200


class UnknownRun(Exception):
    def __init__(self, thread_id: str):
        super().__init__(f"No Run {thread_id}")
        self.thread_id = thread_id


class NotResumable(Exception):
    def __init__(self, status: RunStatus):
        super().__init__(f"A {status} Run can't be resumed")
        self.status = status


class InvalidAnswer(Exception):
    def __init__(self, errors: list[dict]):
        super().__init__(f"Invalid answer: {errors}")
        self.errors = errors


class RunView(Model):
    record: RunRecord
    state: State | None
    pause: Pause | None
    stopped_at: str | None


@asynccontextmanager
async def open_deps(settings: Settings) -> AsyncIterator[Deps]:
    tiers = make_tiers(settings)
    async with make_gateway(settings) as gateway:
        yield Deps(tiers, make_jev(settings, tiers), gateway, settings)


async def _setup_saver(saver: AsyncSqliteSaver) -> None:
    # Two processes racing setup() on a fresh file fail, and a retry clears it.
    for attempt in range(SETUP_ATTEMPTS):
        try:
            return await saver.setup()
        except sqlite3.OperationalError:
            if attempt == SETUP_ATTEMPTS - 1:
                raise
            await asyncio.sleep(0.1 * 2**attempt)


def _config(thread_id: str) -> dict:
    return {
        "configurable": {"thread_id": thread_id},
        "run_name": "scout",
        "tags": ["scout"],
        "metadata": {"thread_id": thread_id},
    }


def _pending_pause(snapshot) -> Pause | None:
    return snapshot.interrupts[0].value if snapshot.interrupts else None


def _stopped_node(snapshot) -> str | None:
    return snapshot.next[0] if snapshot.next else None


class RunHandle:
    def __init__(self, thread_id: str):
        self.thread_id = thread_id
        self._buffer: deque[RunEvent] = deque(maxlen=BUFFER_SIZE)
        self._subscribers: set[asyncio.Queue] = set()
        self._task: asyncio.Task | None = None
        self._stream_ended = False

    def _attach(self, task: asyncio.Task) -> None:
        self._task = task
        task.add_done_callback(lambda _: self._publish_end())

    def _publish(self, event: RunEvent) -> None:
        if not isinstance(event, LIVE_ONLY):
            self._buffer.append(event)
        for queue in self._subscribers:
            queue.put_nowait(event)

    def _publish_end(self) -> None:
        for queue in self._subscribers:
            queue.put_nowait(None)

    async def events(self) -> AsyncIterator[RunEvent]:
        # No await between the snapshot and registering, so no event is missed or seen twice.
        replay = list(self._buffer)
        if self._task.done():
            for event in replay:
                yield event
            return
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        try:
            for event in replay:
                yield event
            while (event := await queue.get()) is not None:
                yield event
        finally:
            self._subscribers.discard(queue)

    async def wait(self) -> RunEvent:
        # asyncio.wait, because awaiting the task directly would cancel the Run with the waiter.
        await asyncio.wait({self._task})
        return self._task.result()

    async def cancel(self) -> Stopped:
        # Past the stream the Run has ended, and its real status is being written. A repeat
        # cancel would break the task out of recording the first one.
        if not self._stream_ended and not self._task.cancelling():
            self._task.cancel()
        await asyncio.wait({self._task})
        terminal = self._task.result()
        return terminal if isinstance(terminal, Stopped) else Stopped(node=None, reason="Run had already ended")


class RunController:
    def __init__(self, settings: Settings, graph: CompiledStateGraph, registry: Registry):
        self._settings = settings
        self._graph = graph
        self._registry = registry
        self._live: set[RunHandle] = set()

    @classmethod
    @asynccontextmanager
    async def open(cls, settings: Settings) -> AsyncIterator["RunController"]:
        settings.runs_db.parent.mkdir(parents=True, exist_ok=True)
        async with open_deps(settings) as deps, aiosqlite.connect(settings.runs_db) as saver_conn:
            saver = AsyncSqliteSaver(saver_conn, serde=JsonPlusSerializer(allowed_msgpack_modules=ALLOWED_MSGPACK))
            await _setup_saver(saver)
            # Autocommit: each transition is one statement, so a cancel can't strand an open
            # write transaction that would block the saver on the same file.
            async with aiosqlite.connect(settings.runs_db, timeout=BUSY_TIMEOUT_S, isolation_level=None) as registry_conn:
                registry = Registry(registry_conn)
                await registry.setup()
                controller = cls(settings, build_graph(deps, saver), registry)
                try:
                    yield controller
                finally:
                    # The connections close next, and a live task still needs them to record its end.
                    await asyncio.gather(*(h.cancel() for h in list(controller._live)), return_exceptions=True)

    async def start(self, request_text: str, focus: list[Dimension] = []) -> RunHandle:
        await self._check_balance()
        thread_id = uuid4().hex[:8]
        lock = take_lock(self._settings.runs_db, thread_id)
        try:
            await self._registry.insert(thread_id, request_text)
        except BaseException:
            lock.close()
            raise
        return self._spawn(thread_id, {"request_text": request_text, "focus": focus}, lock, log_len=0)

    async def resume(self, thread_id: str, answer: dict | None = None) -> RunHandle:
        await self._record(thread_id)  # before the lock, so an unknown ID leaves no lock file
        lock = take_lock(self._settings.runs_db, thread_id)
        try:
            # Read under the lock: another process may have moved the Run on.
            status = (await self._record(thread_id)).status
            snapshot = await self._graph.aget_state(_config(thread_id))
            # The lock is ours, so a row still saying running is stale.
            if status is RunStatus.running:
                status = (await self._reconcile(thread_id, snapshot)).status
            if status not in RESUMABLE:
                raise NotResumable(status)
            command = self._resume_input(_pending_pause(snapshot), answer)
            await self._check_balance()
            await self._registry.transition(thread_id, RunStatus.running)
        except BaseException:
            lock.close()
            raise
        return self._spawn(thread_id, command, lock, log_len=len(snapshot.values.get("run_log", [])))

    async def get_pause(self, thread_id: str) -> Pause | None:
        await self._record(thread_id)
        return _pending_pause(await self._graph.aget_state(_config(thread_id)))

    async def get_run(self, thread_id: str) -> RunView:
        record = await self._reconciled(await self._record(thread_id))
        snapshot = await self._graph.aget_state(_config(thread_id))
        return RunView(
            record=record,
            # Raw values miss every field not yet written, so this fills in the defaults.
            state=State.model_validate(snapshot.values) if snapshot.values else None,
            pause=_pending_pause(snapshot),
            stopped_at=_stopped_node(snapshot) if record.status is RunStatus.failed else None,
        )

    async def list_runs(self, resumable_only: bool = False) -> list[RunRecord]:
        records = [await self._reconciled(record) for record in await self._registry.list_all()]
        if resumable_only:
            return [r for r in records if r.status in RESUMABLE]
        return records

    async def _check_balance(self) -> None:
        # A replayed Run makes no LLM calls, so it must work without OpenRouter.
        if self._settings.replay_cache is None:
            await check_balance(self._settings)

    async def _record(self, thread_id: str) -> RunRecord:
        record = await self._registry.get(thread_id)
        if record is None:
            raise UnknownRun(thread_id)
        return record

    def _resume_input(self, pause: Pause | None, answer: dict | None) -> Command | None:
        if pause is None:
            if answer is not None:
                raise InvalidAnswer([{"msg": "this Run is not waiting for an answer"}])
            return None
        if answer is None:
            raise InvalidAnswer([{"msg": f"the {pause.kind} Pause needs an answer"}])
        try:
            return Command(resume=ANSWERS[pause.kind].model_validate(answer))
        except ValidationError as e:
            raise InvalidAnswer(e.errors()) from e

    async def _reconciled(self, record: RunRecord) -> RunRecord:
        if record.status is not RunStatus.running:
            return record
        try:
            lock = take_lock(self._settings.runs_db, record.thread_id)
        except RunLocked:  # a live task, here or in another process
            return record
        # Held throughout, or a resume could start in the gap and have its live row overwritten.
        try:
            return await self._reconcile(record.thread_id, await self._graph.aget_state(_config(record.thread_id)))
        finally:
            lock.close()

    async def _reconcile(self, thread_id: str, snapshot) -> RunRecord:
        status, error = derive_status(snapshot)
        # A kill can land between the checkpoint and the write, so the files are written here too.
        if status is RunStatus.done:
            self._write_brief(thread_id, snapshot.values)
        await self._registry.reconcile(thread_id, status, error)
        return await self._registry.get(thread_id)

    def _brief_paths(self, thread_id: str) -> list[Path]:
        folder = self._settings.runs_dir / thread_id
        return [folder / "brief.json", folder / "brief.md"]

    def _write_brief(self, thread_id: str, values: dict) -> None:
        state = State.model_validate(values)
        json_path, markdown_path = self._brief_paths(thread_id)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(state.brief.model_dump_json(indent=2), encoding="utf-8")
        markdown_path.write_text(state.brief_markdown or "", encoding="utf-8")

    def _spawn(self, thread_id: str, graph_input, lock: sqlite3.Connection, log_len: int) -> RunHandle:
        handle = RunHandle(thread_id)
        # Eager, so the body's try is entered at once: a task cancelled before its first step
        # would never run its finally, and would keep the lock.
        drive = self._drive(handle, graph_input, lock, ChunkMapper(log_len))
        task = asyncio.Task(drive, loop=asyncio.get_running_loop(), eager_start=True)
        self._live.add(handle)
        task.add_done_callback(lambda _: self._live.discard(handle))
        handle._attach(task)
        return handle

    async def _drive(self, handle: RunHandle, graph_input, lock: sqlite3.Connection, mapper: ChunkMapper) -> RunEvent:
        """Own the graph task: astream lives only here, so closing a subscriber can't touch the Run."""
        thread_id = handle.thread_id
        config = _config(thread_id)
        try:
            try:
                async for mode, chunk in self._graph.astream(
                    graph_input, config, durability="sync", stream_mode=STREAM_MODES
                ):
                    for event in mapper.map(mode, chunk):
                        handle._publish(event)
                handle._stream_ended = True
                terminal = await self._finish(thread_id)
            except asyncio.CancelledError:
                terminal = await self._record_stop(thread_id, "cancelled")
            except Exception as e:
                logger.exception("Run %s failed", thread_id)
                terminal = await self._record_stop(thread_id, f"{type(e).__name__}: {e}"[:ERROR_CHARS])
            if not isinstance(terminal, Paused):  # Paused went out from the stream already
                handle._publish(terminal)
            return terminal
        finally:
            lock.close()

    async def _finish(self, thread_id: str) -> RunEvent:
        snapshot = await self._graph.aget_state(_config(thread_id))
        status = (await self._reconcile(thread_id, snapshot)).status
        if status is RunStatus.paused:
            return Paused(pause=_pending_pause(snapshot))
        return Done(status=status.value, paths=self._brief_paths(thread_id) if status is RunStatus.done else [])

    async def _record_stop(self, thread_id: str, reason: str) -> Stopped:
        snapshot = await self._graph.aget_state(_config(thread_id))
        # Before the first checkpoint there is nothing to rerun, so the Run can't count as resumable.
        status = RunStatus.failed if snapshot.values else RunStatus.aborted
        await self._registry.transition(thread_id, status, reason)
        return Stopped(node=_stopped_node(snapshot), reason=reason)
