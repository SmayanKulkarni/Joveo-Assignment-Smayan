# Research: async persistence and the resume guard

Type: research
Status: resolved
Findings: local branch `research/runtime-async-persistence` (commit `4c64c6f`, not pushed: the repo has no remote), file `research/runtime-async-persistence.md`
Assignee: smayankulkarni05
Blocked by: none

## Question

Do the charting decisions in [Runtime and CLI LLD](../map.md) hold on the pinned LangGraph versions, on Windows?

- `AsyncSqliteSaver` and `AsyncSqliteStore`: construction, lifecycle, and whether both can share one file.
- `LANGGRAPH_STRICT_MSGPACK=true` with `Pause(kind, payload)` as an interrupt value: does the payload rehydrate, and what goes in `allowed_msgpack_modules`?
- How a Pause surfaces through `astream(stream_mode="updates")`, and reading it back with `aget_state` in a fresh process.
- The guard: does a stdlib SQLite connection holding `BEGIN IMMEDIATE` on a lock file refuse a second process at once, and release on a hard kill?
- Two processes writing the same `runs.sqlite` file at once (untested in the HLD research): what fails, and is WAL or a busy timeout needed?

## Answer

Verified by cross-process experiments on Windows.

- **Construction.** The saver and Store share one file on separate connections. An explicit allowlist needs raw `AsyncSqliteSaver(conn, serde=JsonPlusSerializer(allowed_msgpack_modules=[...]))`, because `from_conn_string` takes no `serde`. Construct inside the running loop. Set `LANGGRAPH_STRICT_MSGPACK` before importing langgraph.
- **Pause payload.** The serializer keeps only the outermost model's class, so `payload: Any` or `dict` returns a dict in a fresh process, and `payload: BaseModel` silently loses all fields. Same-process tests hide this. A concrete model or discriminated union rebuilds. Allowlist only the outermost classes: `Pause` and any Pydantic resume value.
- **Surfacing.** `astream` updates end with `{"__interrupt__": (Interrupt(value=...),)}`, with no exception. In a fresh process, `aget_state` gives `next` and `.interrupts`; both are empty after a resume.
- **Guard holds.** A second process is refused in about 0.5 ms at `timeout=0`, and the lock is free about 1 ms after `taskkill /F`. Keep a dedicated connection referenced for the whole Run and never commit on it: GC or `commit()` releases the lock. Probe only with `BEGIN IMMEDIATE`, and check `sqlite_errorname`. Keep it out of `runs.sqlite`.
- **Two writers.** WAL (set by the saver's `setup()`) and a busy timeout are needed. At the 5 s default: no failures at 2×100 or 4×150, 1 of 1,200 at 4×300, no corruption. Racing `setup()` on a fresh file fails, and retry with backoff fixed it (18 of 18). Registry read-then-write must use `BEGIN IMMEDIATE`, or it fails at once with `SQLITE_BUSY_SNAPSHOT`. Stale `running` rows mean the lock file is the liveness test.
- **Untested:** an `Enum` or custom class inside a payload; one connection shared by saver and Store.
