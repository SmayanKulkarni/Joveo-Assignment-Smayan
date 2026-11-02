from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated
from uuid import uuid4

from pydantic import StringConstraints

from talent_scout.analysis.resume import ResumeFacts
from talent_scout.kernel.types import Model

SESSION_DAYS = 30
LOCAL_CSM = "local"

# Same rules as the runs table: TEXT columns and `?` placeholders, created if missing, no migrations.
# ponytail: add Alembic when an existing column has to change.
SCHEMA = [
    """CREATE TABLE IF NOT EXISTS csms (
      id TEXT PRIMARY KEY, google_sub TEXT NOT NULL UNIQUE, email TEXT NOT NULL, created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS sessions (
      token_hash TEXT PRIMARY KEY, csm_id TEXT NOT NULL, expires_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS customers (
      id TEXT PRIMARY KEY, csm_id TEXT NOT NULL, name TEXT NOT NULL, note TEXT,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    # The redacted text stays only to check CSM edits against; no original file is kept.
    """CREATE TABLE IF NOT EXISTS resumes (
      customer_id TEXT PRIMARY KEY, text TEXT NOT NULL, facts TEXT NOT NULL, uploaded_at TEXT NOT NULL)""",
]

CustomerName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
CustomerNote = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


class Csm(Model):
    id: str
    email: str


class Customer(Model):
    id: str
    csm_id: str
    name: str
    note: str | None
    created_at: datetime
    updated_at: datetime


class StoredResume(Model):
    text: str
    facts: ResumeFacts
    uploaded_at: datetime


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _hash(token: str) -> str:
    # Only this goes in the table, so a copy of the database can't be used to sign in.
    return sha256(token.encode()).hexdigest()


class Accounts:
    """CSMs, their sessions and their Customers, in the database the Run registry uses."""

    def __init__(self, run):
        self._run = run

    async def setup(self) -> None:
        for statement in SCHEMA:
            await self._run(statement)

    async def local_csm(self) -> Csm:
        """The one CSM of a login-free install."""
        await self._run(
            "INSERT INTO csms (id, google_sub, email, created_at) VALUES (?, ?, ?, ?) ON CONFLICT (id) DO NOTHING",
            (LOCAL_CSM, LOCAL_CSM, "local@localhost", _now()),
        )
        return Csm(id=LOCAL_CSM, email="local@localhost")

    async def adopt_local_runs(self, name: str = "Local") -> Customer:
        """File every Run that has no Customer under the local one."""
        customer = await self.customer_named(await self.local_csm(), name)
        await self._run("UPDATE runs SET customer_id = ? WHERE customer_id IS NULL", (customer.id,))
        return customer

    async def upsert_csm(self, google_sub: str, email: str) -> Csm:
        # The email is refreshed at each sign-in, because Google lets a person change it.
        rows = await self._run("SELECT id FROM csms WHERE google_sub = ?", (google_sub,))
        if rows:
            await self._run("UPDATE csms SET email = ? WHERE google_sub = ?", (email, google_sub))
            return Csm(id=rows[0]["id"], email=email)
        csm = Csm(id=uuid4().hex, email=email)
        await self._run(
            "INSERT INTO csms (id, google_sub, email, created_at) VALUES (?, ?, ?, ?)", (csm.id, google_sub, email, _now())
        )
        return csm

    async def new_session(self, csm_id: str) -> str:
        await self._run("DELETE FROM sessions WHERE expires_at < ?", (_now(),))
        token = token_urlsafe(32)
        expires = (datetime.now(UTC) + timedelta(days=SESSION_DAYS)).isoformat()
        await self._run("INSERT INTO sessions (token_hash, csm_id, expires_at) VALUES (?, ?, ?)", (_hash(token), csm_id, expires))
        return token

    async def csm_of(self, token: str) -> Csm | None:
        rows = await self._run(
            "SELECT c.id, c.email FROM sessions s JOIN csms c ON c.id = s.csm_id WHERE s.token_hash = ? AND s.expires_at > ?",
            (_hash(token), _now()),
        )
        return Csm.model_validate(rows[0]) if rows else None

    async def end_session(self, token: str) -> None:
        await self._run("DELETE FROM sessions WHERE token_hash = ?", (_hash(token),))

    async def end_sessions_of(self, csm_id: str) -> None:
        await self._run("DELETE FROM sessions WHERE csm_id = ?", (csm_id,))

    async def customers(self, csm: Csm) -> list[Customer]:
        rows = await self._run("SELECT * FROM customers WHERE csm_id = ? ORDER BY created_at DESC", (csm.id,))
        return [Customer.model_validate(row) for row in rows]

    async def customer(self, csm: Csm, customer_id: str) -> Customer | None:
        # The CSM is part of the match, so another CSM's Customer looks the same as one that doesn't exist.
        rows = await self._run("SELECT * FROM customers WHERE id = ? AND csm_id = ?", (customer_id, csm.id))
        return Customer.model_validate(rows[0]) if rows else None

    async def customer_named(self, csm: Csm, name: str) -> Customer:
        """The CSM's first Customer with this name, made if there is none: how the CLI files its Runs."""
        rows = await self._run("SELECT * FROM customers WHERE csm_id = ? AND name = ? ORDER BY created_at", (csm.id, name))
        return Customer.model_validate(rows[0]) if rows else await self.add_customer(csm, name, None)

    async def add_customer(self, csm: Csm, name: str, note: str | None) -> Customer:
        now = _now()
        customer_id = uuid4().hex
        await self._run(
            "INSERT INTO customers (id, csm_id, name, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (customer_id, csm.id, name, note or None, now, now),
        )
        return await self.customer(csm, customer_id)

    async def update_customer(self, customer: Customer, fields: dict) -> Customer:
        merged = {"name": customer.name, "note": customer.note} | fields
        await self._run(
            "UPDATE customers SET name = ?, note = ?, updated_at = ? WHERE id = ?",
            (merged["name"], merged["note"] or None, _now(), customer.id),
        )
        return Customer.model_validate((await self._run("SELECT * FROM customers WHERE id = ?", (customer.id,)))[0])

    async def delete_customer(self, customer_id: str) -> None:
        await self.delete_resume(customer_id)
        await self._run("DELETE FROM customers WHERE id = ?", (customer_id,))

    async def resume(self, customer_id: str) -> StoredResume | None:
        rows = await self._run("SELECT text, facts, uploaded_at FROM resumes WHERE customer_id = ?", (customer_id,))
        return StoredResume.model_validate({**rows[0], "facts": ResumeFacts.model_validate_json(rows[0]["facts"])}) if rows else None

    async def save_resume(self, customer_id: str, text: str, facts: ResumeFacts, *, keep_date: bool = False) -> None:
        await self._run(
            "INSERT INTO resumes (customer_id, text, facts, uploaded_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (customer_id) DO UPDATE SET text = excluded.text, facts = excluded.facts"
            + ("" if keep_date else ", uploaded_at = excluded.uploaded_at"),
            (customer_id, text, facts.model_dump_json(), _now()),
        )

    async def delete_resume(self, customer_id: str) -> bool:
        gone = bool(await self._run("SELECT 1 FROM resumes WHERE customer_id = ?", (customer_id,)))
        await self._run("DELETE FROM resumes WHERE customer_id = ?", (customer_id,))
        return gone

    async def owner_of_run(self, thread_id: str) -> str | None:
        rows = await self._run(
            "SELECT c.csm_id FROM runs r JOIN customers c ON c.id = r.customer_id WHERE r.thread_id = ?", (thread_id,)
        )
        return rows[0]["csm_id"] if rows else None
