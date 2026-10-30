import asyncio
from types import SimpleNamespace

import aiosqlite
import pytest

from talent_scout.runtime.registry import Registry, RunStatus, derive_status


def snapshot(*, interrupts=(), next=(), values=None):
    return SimpleNamespace(interrupts=interrupts, next=next, values=values or {})


@pytest.mark.parametrize(
    "snap, expected",
    [
        (snapshot(interrupts=("pause",), next=("clarify",), values={"request_text": "x"}), (RunStatus.paused, None)),
        (snapshot(next=("plan",), values={"request_text": "x"}), (RunStatus.failed, "process stopped mid-Run")),
        (snapshot(), (RunStatus.aborted, "killed before the first checkpoint")),
        (snapshot(values={"request_text": "x", "brief": object()}), (RunStatus.done, None)),
        (snapshot(values={"request_text": "x"}), (RunStatus.aborted, None)),
    ],
    ids=["paused", "failed", "killed-early", "done", "aborted"],
)
def test_derive_status(snap, expected):
    assert derive_status(snap) == expected


def test_transition_updates_status_error_and_updated_at(tmp_path):
    async def go():
        async with aiosqlite.connect(tmp_path / "runs.sqlite") as conn:
            registry = Registry(conn)
            await registry.setup()
            await registry.insert("t1", "x" * 100)
            before = await registry.get("t1")
            # Windows' clock only ticks every ~15 ms, so a tighter gap could read as no change.
            await asyncio.sleep(0.02)
            await registry.transition("t1", RunStatus.failed, "boom")
            return before, await registry.get("t1")

    before, after = asyncio.run(go())

    assert (before.status, before.error, len(before.summary)) == (RunStatus.running, None, 80)
    assert (after.status, after.error) == (RunStatus.failed, "boom")
    assert after.created_at == before.created_at
    assert after.updated_at > before.updated_at


def test_get_unknown_thread_is_none(tmp_path):
    async def go():
        async with aiosqlite.connect(tmp_path / "runs.sqlite") as conn:
            registry = Registry(conn)
            await registry.setup()
            return await registry.get("nope")

    assert asyncio.run(go()) is None
