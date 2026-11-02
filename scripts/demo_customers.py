"""File the sample Runs under made-up Customers, so a demo shows a CSM's book of clients. Safe to run again.

Run it with the same env as the server: a login-free `scout serve` on SQLite needs `DATABASE_URL=` set empty here.
"""
import asyncio
from contextlib import asynccontextmanager

import aiosqlite
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from talent_scout.kernel.settings import Settings
from talent_scout.runtime.accounts import Accounts
from talent_scout.runtime.controller import RunController
from talent_scout.runtime.registry import Registry

# Invented people. Each Run id is a sample already in the app; ids that aren't in this install are skipped.
CUSTOMERS = {
    "Priya Nair": ("Analyst moving over from banking ops, Mumbai", ["60910cce", "f62fbcbe"]),
    "Rohan Desai": ("Final-year BBA, wants a marketing internship", ["30a3efec", "fd9c2370"]),
    "Ananya Iyer": ("Backend developer, 3 years, open to relocate", ["6bc57b0a"]),
    "Daniel Brooks": ("NLP PhD, looking at US ML roles", ["d5379152", "766b46da"]),
}


@asynccontextmanager
async def registry(settings: Settings):
    if settings.database_url:
        kwargs = {"autocommit": True, "row_factory": dict_row, "prepare_threshold": 0}
        async with AsyncConnectionPool(settings.database_url, min_size=1, max_size=1, kwargs=kwargs) as pool:
            yield Registry(pool)
    else:
        async with aiosqlite.connect(settings.runs_db, isolation_level=None) as conn:
            yield Registry(conn)


async def main():
    settings = Settings()
    moved = []
    async with registry(settings) as reg:
        accounts = Accounts(reg.run)
        csm = await accounts.local_csm()
        for name, (note, run_ids) in CUSTOMERS.items():
            customer = await accounts.customer_named(csm, name)
            await accounts.update_customer(customer, {"note": note})
            for run_id in run_ids:
                await reg.run("UPDATE runs SET customer_id = ? WHERE thread_id = ?", (customer.id, run_id))
            moved.append(customer.id)
            print(f"{name}: {len(run_ids)} Runs")
    # Moving a Run by hand skips the rebuild a finished Run triggers, so each profile is learned here instead.
    async with RunController.open(settings) as controller:
        for customer_id in moved:
            await controller.relearn(customer_id)


# psycopg can't run on the Proactor loop Windows defaults to.
asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
