import asyncio
import queue
import threading
from contextlib import AsyncExitStack
from dataclasses import dataclass

import streamlit as st

from talent_scout.kernel.settings import get_settings
from talent_scout.kernel.types import Dimension
from talent_scout.runtime.controller import RunController, RunHandle, RunView
from talent_scout.runtime.events import RunEvent
from talent_scout.runtime.registry import RunRecord


@dataclass
class Live:
    """A Run in flight: events end with None once the Run has stopped, paused or finished."""

    thread_id: str
    events: queue.Queue[RunEvent | None]


class Bridge:
    """One Controller on a background loop, so Streamlit's script threads can share the Runs it owns."""

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True).start()
        # Never closed: the loop thread is a daemon and lives as long as the process.
        self._pumps: set[asyncio.Task] = set()
        self._stack = AsyncExitStack()
        self._controller = self._call(self._stack.enter_async_context(RunController.open(get_settings())))

    def _call(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def _follow(self, handle: RunHandle) -> Live:
        events: queue.Queue[RunEvent | None] = queue.Queue()

        async def pump():
            try:
                async for event in handle.events():
                    events.put(event)
            finally:  # the reader blocks until it sees the end marker
                events.put(None)

        # Called on the loop; the loop holds tasks weakly, so the set keeps the pump alive.
        task = asyncio.create_task(pump())
        self._pumps.add(task)
        task.add_done_callback(self._pumps.discard)
        return Live(handle.thread_id, events)

    def start(self, request: str, focus: list[Dimension]) -> Live:
        return self._call(self._start(request, focus))

    def resume(self, thread_id: str, answer: dict | None) -> Live:
        return self._call(self._resume(thread_id, answer))

    # The handle is created on the loop, and its events() must be read from there too.
    async def _start(self, request: str, focus: list[Dimension]) -> Live:
        return self._follow(await self._controller.start(request, focus))

    async def _resume(self, thread_id: str, answer: dict | None) -> Live:
        return self._follow(await self._controller.resume(thread_id, answer))

    def get_run(self, thread_id: str) -> RunView:
        return self._call(self._controller.get_run(thread_id))

    def list_runs(self) -> list[RunRecord]:
        return self._call(self._controller.list_runs())


@st.cache_resource
def get_bridge() -> Bridge:
    return Bridge()
