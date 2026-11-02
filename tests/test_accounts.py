import asyncio

import aiosqlite

from talent_scout.runtime.accounts import Accounts
from talent_scout.runtime.registry import Registry

OLD_RUNS = """CREATE TABLE runs (thread_id TEXT PRIMARY KEY, summary TEXT NOT NULL, status TEXT NOT NULL,
  error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""


def test_an_older_runs_table_gains_its_column_and_its_runs_move_to_local(tmp_path):
    async def go():
        async with aiosqlite.connect(tmp_path / "runs.sqlite") as conn:
            await conn.execute(OLD_RUNS)
            await conn.execute("INSERT INTO runs VALUES ('old', 's', 'done', NULL, '2026-01-01', '2026-01-01')")
            registry = Registry(conn)
            await registry.setup()
            await registry.setup()  # idempotent
            accounts = Accounts(registry.run)
            await accounts.setup()
            local = await accounts.adopt_local_runs()
            csm = await accounts.local_csm()
            assert (await registry.get("old")).customer_id == local.id
            assert [r.thread_id for r in await registry.list_all(csm_id=csm.id)] == ["old"]
            assert await registry.list_all(csm_id="someone-else") == []
            assert (await accounts.adopt_local_runs()).id == local.id  # no second "Local"

    asyncio.run(go())
