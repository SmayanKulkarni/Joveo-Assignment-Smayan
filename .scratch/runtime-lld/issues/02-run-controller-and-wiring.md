# Run Controller API and wiring

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

What is the Run Controller's exact API, and how is the graph wired?

- Signatures of start, resume, stream events and get state, and what each returns.
- Status transitions, and when the registry is written relative to the checkpoint.
- Failure handling: `LLMExhausted`, auth errors and bugs stopping a Run; where `check_balance` refuses.
- Wiring table from HLD §4, `owned()` wrapping, and the stub-node skeleton that proves durable resume before any stage exists.
- `Pause.payload` typing, given [the research](01-research-async-persistence-and-guard.md): `payload: dict` plus `kind` with the stage calling `model_validate` (keeps ownership in the stage), or a discriminated union in Runtime (typed, but Runtime imports every stage's payload).
- Running the graph in its own task, since [closing a stream cancels the Run](05-research-live-streaming-sources.md), and whether the Controller stores events so a reloaded client has history.
- Lifecycle of `Deps` and the Gateway's `async with`.

## Answer

Decided by grilling.

- **Identity and storage.**
  - Thread ID is `uuid4().hex[:8]` (typable, filename-safe, URL-safe).
  - The registry is a plain `runs` table in `runs.sqlite` on its own connection, not a `("runs",)` Store namespace (this changes HLD §8): `thread_id` PK, `summary` (first 80 chars of the request), `status`, `error`, `created_at`, `updated_at`. A transition is one atomic `UPDATE`, so no read-then-write.
  - `AsyncSqliteStore` is not opened until the preferences slice (pass 6); the Kernel §10 Store items move there.
  - On `done`, the Controller writes `runs/<thread_id>/brief.json` and `brief.md` (idempotent) and puts the paths on the `Done` event.
- **API.** `async with RunController.open(settings) as rc`:
  - `start(request_text, focus=[]) -> RunHandle`
  - `resume(thread_id, answer=None) -> RunHandle`
  - `get_pause(thread_id) -> Pause | None`
  - `get_run(thread_id) -> RunView` (record plus `State.model_validate(values)`)
  - `list_runs(resumable_only=False) -> list[RunRecord]`, reconciled on read
  - Errors, all raised before any state change: `RunLocked`, `NotResumable(status)`, `InvalidAnswer(errors)`, `BalanceTooLow`.
- **Task and events.**
  - The Controller owns the graph task, so closing a subscription never cancels the Run.
  - `RunHandle`: `thread_id`, `events()` (replays the buffer, then live), `wait()` (returns the terminal event), `cancel()`.
  - History is an in-memory buffer per active Run in this process, at most 5,000 events, oldest dropped, terminal events kept. Nothing is persisted: a reloaded client rebuilds from `get_run` (`run_log`, pending Pause, status).
  - Pass 1 events: `NodeDone(node)`, `Paused(pause)`, `Done(status, paths)` with status `done | aborted`, `Stopped(node, reason)`. Tokens, tool calls and reasoning are decided in Clients flow.
  - `cancel()` cancels the task, writes `failed` with error `cancelled`, and releases the lock.
- **Status and registry timing.**
  - `running` is written after the lock and `check_balance`, just before the task starts. The final status is written after the task ends, from `aget_state`: pending interrupt → `paused`; `next` empty with a `brief` → `done`; `next` empty without → `aborted`; exception → `failed`. The registry lags the checkpoint and never leads it.
  - Reconcile on read: a `running` row with a free lock is stale, so the real status is derived from `aget_state` and written back.
  - Resumable: `paused` and `failed`. A `failed` Run resumes with `astream(None, ...)`, rerunning only the node that stopped.
- **Resume order.** Take the lock, read the pending Pause, validate the answer against that kind's answer model, `check_balance`, write `running`, spawn the task. The lock is held until the task ends. The `get_*` and `list_runs` calls are read-only and never lock.
- **Failures.** `check_balance` runs at the top of `start` and `resume` and raises `BalanceTooLow` before anything changes. Inside the task, any `Exception` (`LLMExhausted`, 401, `StateWriteError`, bugs) writes `failed` with a short `error` (class and message, about 200 chars), logs the traceback, and emits `Stopped(node, reason)` with `node` from `aget_state().next`. Nothing goes in `run_log`. There is no balance check between nodes.
- **Pause typing.** `Pause` is a discriminated union by `kind` (`ClarifyPause | PlanReviewPause | LowDataPause`), each with a concrete payload model; the Controller validates answers per kind and resumes with the Pydantic answer model. Payload and answer models live in the owning stage's `types.py`, and the skeleton uses stubs in Runtime's `testing.py`. `allowed_msgpack_modules` lists `Pause` and the answer classes.
- **Wiring.**
  - Each stage exports `make_nodes(deps) -> dict[str, Node]` and `ROUTERS: dict[str, Router]` keyed by the node they follow.
  - The whole HLD §4 graph is compiled from one edge table in `runtime/graph.py` from day one, with `nodes = {**stub_nodes, **real_nodes}`, so a missing stage runs as a stub and landing a stage needs no wiring change.
  - One owner table wraps every node and router in `owned(name, owner)`. Owners: `request_plan` for `intake`, `clarity_check`, `clarify`, `plan`, `plan_review`; `collection` for `fetch_agent`, `tools`, `collect`, `relevance`, `broaden`, `low_data_review`; `analysis` for `batch_extract`, `stats`; `brief` for `write_brief`, `critic`, `render`.
- **Lifecycle.** `RunController.open` builds Deps (`make_tiers`, `make_jev`, `async with make_gateway`), then the saver (raw `AsyncSqliteSaver` with an explicit serde, `setup()` retried with backoff) and the registry connection, and compiles the graph once. It closes everything in reverse order. The CLI opens one Controller per `asyncio.run`; Streamlit holds one on a background loop for the process lifetime. Fixed per-call config: `thread_id`, `run_name="scout"`, tags, `thread_id` in LangSmith metadata, `durability="sync"`, `stream_mode=["updates","messages","custom"]`. `recursion_limit` stays at the default (10007), so there is no cap to set.
- **Skeleton proof.** Stub nodes each write one `log` note and a minimal valid slice, and the three Pause stubs interrupt once each. A `pytest` test with no LLM or network (fake Deps, stubbed `check_balance`) starts a Run in a subprocess, kills it with `taskkill /F` at each Pause, then fetches the typed Pause with `get_pause` and resumes in a fresh process through all three Pauses to `done`. It also checks that a second process resuming a running thread gets `RunLocked`. A separate live smoke script runs the same flow with the real `check_balance`.
