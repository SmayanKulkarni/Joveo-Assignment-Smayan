import asyncio
import os

import pytest
from pydantic import ValidationError

from talent_scout.kernel.testing import make_settings
from test_controller import open_fake_deps, to_terminal
from talent_scout.runtime import controller as controller_module
from talent_scout.runtime.controller import RunController
from talent_scout.runtime.events import Paused
from talent_scout.runtime.registry import RunStatus
from talent_scout.runtime.testing import ANSWER_FOR, pass_balance

# Opt-in, and never the production URL: the test writes real Runs.
# psycopg can't use the Proactor loop that Windows defaults to.
URL = os.environ.get("TEST_DATABASE_URL")


def test_render_refuses_to_start_without_a_database_and_a_replay_never_meets_one():
    with pytest.raises(ValidationError, match="database_url must be set on Render"):
        make_settings(render_external_hostname="scout.onrender.com")
    with pytest.raises(ValidationError, match="can't both be set"):
        make_settings(database_url="postgresql://x/y", replay_cache="cache.sqlite")
    make_settings(render_external_hostname="scout.onrender.com", database_url="postgresql://x/y")
    make_settings(render_external_hostname="scout.onrender.com", demo=True)


@pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL is not set")
def test_a_run_started_before_a_restart_is_opened_after_it_and_resumes(tmp_path, monkeypatch):
    monkeypatch.setattr(controller_module, "open_deps", open_fake_deps)
    monkeypatch.setattr(controller_module, "check_balance", pass_balance)
    settings = make_settings(database_url=URL, runs_db=tmp_path / "unused.sqlite", runs_dir=tmp_path / "runs", gateway_db=tmp_path / "gw.sqlite")

    async def before_restart():
        async with RunController.open(settings) as controller:
            handle = await controller.start("Engineer, Texas")
            assert isinstance(terminal := await handle.wait(), Paused)
            return handle.thread_id, terminal.pause.kind

    async def after_restart(thread_id, kind):
        async with RunController.open(settings) as controller:
            assert (await controller.get_run(thread_id)).record.status is RunStatus.paused
            handle = await controller.resume(thread_id, ANSWER_FOR[kind])
            await to_terminal(controller, handle)
            return (await controller.get_run(thread_id)).record.status

    thread_id, kind = asyncio.run(before_restart(), loop_factory=asyncio.SelectorEventLoop)
    assert asyncio.run(after_restart(thread_id, kind), loop_factory=asyncio.SelectorEventLoop) is RunStatus.done
    assert not settings.runs_db.exists()  # nothing of the Run is on the local disk
