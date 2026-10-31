# Opening the Store

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 02

## Question

HLD §3 gives Runtime the SQLite Store, but [Run Controller API and wiring](02-run-controller-and-wiring.md) only says it isn't opened until pass 6. How does `RunController.open` open it, and how does a node reach it, given that nodes close over `Deps` and go through `owned()`? What a preference contains stays with the Long-term memory LLD.

## Answer

Decided by the agent, on the user's instruction, after an offline probe on the pinned versions.

- **Opening.** From pass 6, `RunController.open` opens a raw `AsyncSqliteStore` on `runs_db`, on its own `aiosqlite` connection, between the registry and `build_graph`, and closes it in reverse order. Its `setup()` shares the saver's retry.
- **The connection must be autocommit** (`isolation_level=None`), the way `from_conn_string` opens it, with a 5 s busy timeout. On a default connection `setup()` leaves a transaction open, so in the probe the saver's next checkpoint write failed with "database is locked", and the Store's own next write fails with "cannot start a transaction within a transaction".
- **Reaching a node.** `build_graph(deps, saver, store=None)` passes it to `builder.compile(checkpointer=saver, store=store)`. A node that needs it declares `runtime: Runtime` and uses `runtime.store`. It does not go in `Deps`: this is LangGraph's own route, and nodes that don't use it don't change.
- **`owned()` needs no change.** Its `functools.wraps` keeps the signature LangGraph reads, so `runtime` is still injected.
- **Values** stay as already decided: written with `model_dump(mode="json")`, read with `model_validate`. They are plain JSON, so nothing joins `ALLOWED_MSGPACK`.
- **Nothing is opened before pass 6.** No stage reads it yet, so `store` stays `None` until then.

Probe results:

| Check | Result |
|---|---|
| A node behind `owned()` reads and writes through `runtime.store` | Works |
| A preference written on one thread is read by another, after both connections reopen | Works |
| A Pause and resume with the saver and Store on one file, on separate connections | Works |
| Default connection instead of autocommit | Fails, as above |
| 4 processes racing `setup()` on a fresh file, then 100 writes each | No failures in the one run. The retry stays, since the saver's race did fail |
