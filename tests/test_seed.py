import asyncio
import sqlite3
from pathlib import Path

import pytest

from talent_scout.kernel.testing import make_settings
from talent_scout.runtime import controller as controller_module
from talent_scout.runtime.controller import RunController
from talent_scout.runtime.testing import open_fake_deps, pass_balance

SEED = Path(__file__).resolve().parents[1] / "seed"


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setattr(controller_module, "open_deps", open_fake_deps)
    monkeypatch.setattr(controller_module, "check_balance", pass_balance)
    return make_settings(
        runs_db=tmp_path / "runs.sqlite", runs_dir=tmp_path / "runs", gateway_db=tmp_path / "gw.sqlite", seed_dir=SEED
    )


def test_a_fresh_install_starts_with_the_sample_runs_and_reopening_adds_no_more(settings):
    ids = {r[0] for r in sqlite3.connect(SEED / "seed.sqlite").execute("SELECT thread_id FROM runs")}
    assert ids

    async def go():
        async with RunController.open(settings) as controller:
            assert {r.thread_id for r in await controller.list_runs()} == ids
            for thread_id in ids:
                view = await controller.get_run(thread_id)
                assert view.state.brief is not None
                assert controller.brief_paths(thread_id)[0].is_file()

    asyncio.run(go())
    asyncio.run(go())  # the second open must not duplicate or fail
