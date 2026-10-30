# Runtime and Clients LLD

The low-level design of Runtime and Clients (components G and H in [HLD](../HLD.md) §3 and §8), precise enough to build from. Items marked ⏳ belong to the named LLD. Deliberate deferrals live in [future-scope.md](future-scope.md). Shared types, `owned()` and settings come from the [Kernel LLD](kernel.md).

Source tickets (each holds the full reasoning):
- [Run Controller API and wiring](../../.scratch/runtime-lld/issues/02-run-controller-and-wiring.md)
- [Clients flow](../../.scratch/runtime-lld/issues/03-clients-flow.md)
- Research: [async persistence and the resume guard](../../.scratch/runtime-lld/issues/01-research-async-persistence-and-guard.md), [live streaming sources](../../.scratch/runtime-lld/issues/05-research-live-streaming-sources.md), [LangGraph persistence and resume](../../.scratch/talent-scout-hld/issues/15-research-langgraph-persistence-and-resume.md)

## 1. What Runtime and Clients are

Runtime wires and runs the graph, and owns threads and the registry. It writes nothing in graph state except the input fields. Clients call only the Run Controller, never the graph, and never see a LangGraph chunk.

Runtime owns:
- the graph's edge table, owner table and compile
- the Pause envelope, the answer check, and re-showing a Pause on return
- the Run Controller, the run registry and the resume guard
- `RunEvent` and the mapping from stream chunks to it
- the stub-node skeleton

Clients own the CLI and a thin Streamlit page. Neither owns any state.

They do **not** own:
- node bodies, or each Pause's payload and answer fields (stage LLDs)
- what each `focus` value changes ([Request & Plan LLD](request-plan.md) §8). Clients only pass it through.
- `AsyncSqliteStore`: not opened until preferences land in pass 6 (⏳ Long-term memory)
- infra shell internals. Its only seam is the Run Controller.

## 2. Layout

```
src/talent_scout/
  __init__.py              # sets LANGGRAPH_STRICT_MSGPACK before anything imports langgraph
  kernel/events.py         # emit()
  runtime/
    deps.py                # Deps
    pause.py               # Pause union, ANSWERS
    events.py              # RunEvent, chunk mapping
    graph.py               # edge table, owner table, build_graph()
    registry.py            # runs table, derive_status()
    guard.py               # per-thread lock
    controller.py          # RunController, RunHandle, errors
    testing.py             # stub_nodes, STUB_ROUTERS, fake_deps
  clients/
    cli.py                 # argparse, `scout` entry point
    pauses.py              # plain text of each Pause payload, shared by both clients
    streamlit_app.py       # pass 2
    streamlit_bridge.py    # pass 2
  request_plan/types.py    # stub payload and answer models at their final path
  collection/types.py      # same
```

- **Import direction:** `runtime/graph.py` imports the stages' `make_nodes`. Stages import only `runtime/deps.py` and `runtime/pause.py`, which never import `graph.py`, so nothing loops. `runtime/pause.py` imports only stage `types.py` modules.
- **Strict msgpack is set in the package `__init__.py`,** because it must be in the environment before langgraph is first imported, and any `talent_scout.*` import runs that file first.
- **Dependencies:** `rich` in pass 1, `streamlit` in a `streamlit` dependency group in pass 2. `aiosqlite` is already there through `langgraph-checkpoint-sqlite`; pin it.

## 3. Stage contract

```python
@dataclass(frozen=True)
class Deps:
    tiers: Tiers
    jev: Jev
    gateway: JobsGateway
    settings: Settings

Node = Callable[..., Awaitable[dict]]
Router = Callable[[State], str | list[Send]]

# each stage exports:
def make_nodes(deps: Deps) -> dict[str, Node]: ...
ROUTERS: dict[str, Router]        # keyed by the node they follow
```

Nodes close over `Deps`, and there is no `context_schema`. A stage exports only what it has built. A stage's pass 1 export includes a pass-through for any Pause it hasn't built yet (such as `plan_review` returning `{}`), so a real Run doesn't stop at a stub Pause.

## 4. Graph wiring (`runtime/graph.py`)

The whole HLD §4 graph compiles from one table from day one. A missing stage runs as a stub, so landing a stage needs no wiring change.

```python
nodes = {**stub_nodes(), **real_nodes}
routers = {**STUB_ROUTERS, **real_routers}

EDGES = [
    (START, "intake"), ("intake", "clarity_check"), ("clarify", "intake"),
    ("plan", "plan_review"), ("tools", "fetch_agent"), ("collect", "relevance"),
    ("broaden", "fetch_agent"), ("batch_extract", "stats"), ("stats", "write_brief"),
    ("write_brief", "critic"), ("render", END),
]
CONDITIONAL = {
    "clarity_check":   ["clarify", "plan", END],
    "plan_review":     ["fetch_agent", "plan", END],
    "fetch_agent":     ["tools", "collect"],
    "relevance":       ["batch_extract", "broaden", "low_data_review"],
    "low_data_review": ["broaden", "batch_extract", "stats", END],
    "critic":          ["write_brief", "render"],
}
OWNERS = {
    "request_plan": ["intake", "clarity_check", "clarify", "plan", "plan_review"],
    "collection":   ["fetch_agent", "tools", "collect", "relevance", "broaden", "low_data_review"],
    "analysis":     ["batch_extract", "stats"],
    "brief":        ["write_brief", "critic", "render"],
}
```

`build_graph(deps, saver)` wraps every node and router in `owned(name, owner)` from `OWNERS` and compiles once, on `State`. The list of targets goes to `add_conditional_edges`, because a router returning `Send` can't be read for its destinations.

**`"analyse"`.** Collection's routers return this plain outcome where they would fan out, because `Send` payloads and batching belong to Analysis and a stage can't import another. `build_graph` wraps those two routers:

```python
def routed(state):
    out = router(state)
    return fan_out(state) if out == "analyse" else out
```

`fan_out` comes from ⏳ Analysis and also sends zero Postings to `stats`, which is why `low_data_review` keeps its `stats` target. Until Analysis lands, the stub in `runtime/testing.py` returns `"stats"`. See the [Collection LLD](collection.md) §4.

**Fixed per-call config:** `thread_id`, `run_name="scout"`, tags, `thread_id` in LangSmith metadata, `durability="sync"`, `stream_mode=["updates", "messages", "custom", "tasks"]`. `recursion_limit` stays at the default (10007). All four modes are on from pass 1, and pass 3 only adds their mapping.

## 5. Pause protocol (`runtime/pause.py`)

Every `interrupt()` carries one concrete model:

```python
class ClarifyPause(Model):
    kind: Literal["clarify"] = "clarify"
    payload: ClarifyPayload
class PlanReviewPause(Model):
    kind: Literal["plan_review"] = "plan_review"
    payload: PlanReviewPayload
class LowDataPause(Model):
    kind: Literal["low_data_review"] = "low_data_review"
    payload: LowDataPayload

Pause = Annotated[ClarifyPause | PlanReviewPause | LowDataPause, Field(discriminator="kind")]
ANSWERS = {"clarify": ClarifyAnswer, "plan_review": PlanReviewAnswer, "low_data_review": LowDataAnswer}
```

- **Payload and answer models live in the owning stage's `types.py`.** Runtime creates them as stubs at their final path, the way `analysis/types.py` and `brief/types.py` already work, because checkpoints store class paths. Stage LLDs own the fields. Stub shapes:
  - `ClarifyPayload`, `ClarifyAnswer`, `PlanReviewPayload`, `PlanReviewAnswer`: final, in [Request & Plan LLD](request-plan.md) §3
  - `LowDataPayload`, `LowDataAnswer`: final, in [Collection LLD](collection.md) §3. Their stubs start as `LowDataPayload(count: int, target: int)` and `LowDataAnswer(action: broaden | continue | abort)`.
- **A concrete union, not `payload: dict`.** The serializer keeps only the outermost model's class, so an untyped payload comes back from a fresh process as a dict.
- **Allowlist:** the three Pause classes and the three answer classes go in `JsonPlusSerializer(allowed_msgpack_modules=[...])`. Nested models don't need listing, but enums inside them (`PlanAction`, `RequestField`) do, or each load logs a "blocked" warning.
- **Answers:** the Controller checks a client's answer with `ANSWERS[pause.kind].model_validate(...)` and resumes with `Command(resume=<answer model>)`, so a stage node receives a typed answer. Clients render by `kind`.
- **Pause nodes stay pure** (HLD §8). Resume re-runs the whole node, which would repeat tokens and cost for any LLM call placed before `interrupt()`.

## 6. Run Controller API (`runtime/controller.py`)

```python
class RunStatus(StrEnum): running, paused, done, aborted, failed

class RunRecord(Model):
    thread_id: str; summary: str; status: RunStatus; error: str | None
    created_at: datetime; updated_at: datetime

class RunView(Model):
    record: RunRecord
    state: State | None      # State.model_validate(values); None before the first checkpoint
    pause: Pause | None
    stopped_at: str | None   # for failed Runs, from aget_state().next

class RunController:
    @classmethod
    @asynccontextmanager
    async def open(cls, settings) -> AsyncIterator["RunController"]: ...

    async def start(self, request_text: str, focus: list[Dimension] = []) -> "RunHandle": ...
    async def resume(self, thread_id: str, answer: dict | None = None) -> "RunHandle": ...
    async def get_pause(self, thread_id: str) -> Pause | None: ...
    async def get_run(self, thread_id: str) -> RunView: ...
    async def list_runs(self, resumable_only: bool = False) -> list[RunRecord]: ...   # newest first

class RunHandle:
    thread_id: str
    def events(self) -> AsyncIterator[RunEvent]: ...   # replays the buffer, then live
    async def wait(self) -> RunEvent: ...              # the terminal event
    async def cancel(self) -> Stopped: ...
```

**Errors, all raised before any state change:** `UnknownRun(thread_id)`, `RunLocked(thread_id)`, `NotResumable(status)`, `InvalidAnswer(errors)`, and the Kernel's `BalanceTooLow`. A network failure in `check_balance` also propagates from `start` or `resume`.

- **Thread ID** is `uuid4().hex[:8]`: typable, filename-safe, URL-safe.
- **`start`:** `check_balance`, new thread ID, lock, insert the row as `running`, spawn the task with input `{"request_text": ..., "focus": ...}`.
- **`resume`:** take the lock, read the pending Pause, validate the answer against that kind (`None` on a Pause, or an answer on a `failed` Run, is `InvalidAnswer`), `check_balance`, write `running`, spawn the task. A `paused` Run resumes with `Command(resume=answer)`. A `failed` Run resumes with `astream(None, ...)`, which reruns only the node that stopped; finished `Send` branches come back cached.
- **`check_balance` is skipped when `replay_cache` is set,** so a replayed Run works without OpenRouter. It runs nowhere between nodes.
- **`get_*` and `list_runs` are read-only** and never lock, so `scout show` works on a Run that's open elsewhere.
- **`get_run`** wraps values with `State.model_validate`, because `get_state().values` is a raw dict with unwritten defaults missing (Kernel §10).

### Task and event buffer

The Controller owns the graph task, so closing a subscription never cancels the Run. `astream` is consumed only inside that task.

- **Buffer:** one `deque(maxlen=5000)` per active Run in this process. Oldest events drop first, and the terminal event is always newest, so it stays. Nothing is persisted: a reloaded client rebuilds from `get_run` (`run_log`, pending Pause, status).
- **Subscribers:** each `events()` call takes a snapshot of the buffer and registers its own `asyncio.Queue`, with no `await` between the two. `Token` and `Reasoning` go only to subscribers, never the buffer, because one `fetch_agent` turn could otherwise push out everything else.
- **`cancel()`** cancels the task, writes `failed` with error `cancelled`, releases the lock, and returns the `Stopped` event.

## 7. Registry and status (`runtime/registry.py`)

A plain table in `runs.sqlite`, on its own `aiosqlite` connection and not a Store namespace:

```sql
CREATE TABLE IF NOT EXISTS runs (
  thread_id  TEXT PRIMARY KEY,
  summary    TEXT NOT NULL,      -- first 80 chars of the request
  status     TEXT NOT NULL,
  error      TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

A transition is one atomic `UPDATE`, so there is no read-then-write. The table is an index: `aget_state` is the truth, and the registry lags the checkpoint but never leads it.

- `running` is written after the lock and `check_balance`, just before the task starts.
- The final status is written after the task ends, by one pure function:

```python
def derive_status(snapshot) -> tuple[RunStatus, str | None]:
    if snapshot.interrupts: return RunStatus.paused, None
    if snapshot.next: return RunStatus.failed, "process stopped mid-Run"
    if not snapshot.values: return RunStatus.aborted, "killed before the first checkpoint"
    if snapshot.values.get("brief"): return RunStatus.done, None
    return RunStatus.aborted, None
```

- **A task exception** skips `derive_status` and writes `failed` with a short error (§9).
- **Reconcile on read.** In `get_run` and `list_runs`, a `running` row whose lock is free is stale: derive the real status and write it back with `... WHERE thread_id = ? AND status = 'running'`. A live task's lock is busy, so its row stays `running`, in this process or another. No heartbeat.
- **Resumable** means `paused` or `failed`. A killed Run reconciles to one of them, so it stays resumable.
- **On `done`,** the Controller writes `runs/<thread_id>/brief.json` and `brief.md` and puts the paths on the `Done` event. This is idempotent, and reconcile does it too, since a kill can land between the checkpoint and the write.

**Limit:** a Run killed in the tiny window before its first checkpoint can't resume, because the full request text was never stored. It shows as `aborted` with that error.

## 8. Resume guard (`runtime/guard.py`)

A per-thread lock using a stdlib SQLite connection on `.cache/locks/<thread>.lock`, kept out of `runs.sqlite`.

```python
conn = sqlite3.connect(path, timeout=0, isolation_level=None)
conn.execute("BEGIN IMMEDIATE")     # SQLITE_BUSY means RunLocked
```

- A second process is refused in about 0.5 ms, and the lock frees about 1 ms after `taskkill /F`.
- Keep the connection referenced for the whole Run and never commit on it: GC or `commit()` releases the lock. `check_same_thread` stays default, since one loop thread both takes and releases it.
- Check `sqlite_errorname` to tell busy from other failures.
- **The lock is held only while the task runs,** not while a Pause waits for an answer. Two clients sitting at one Pause is safe, because the second `resume` either hits the lock or finds the Run no longer paused.
- The probe for reconcile takes the lock and closes straight away. A `resume` racing that probe could see a false `RunLocked` for a few milliseconds, and retrying clears it.
- Lock files stay on disk: they're empty and harmless.

## 9. Failures

Inside the task, any `Exception` (`LLMExhausted`, a 401, `StateWriteError`, bugs) does the same thing:
1. Write `failed` with a short error: class and message, about 200 chars.
2. Log the traceback.
3. Emit `Stopped(node, reason)`, with `node` from `aget_state().next`.

Nothing goes in `run_log`, because backend errors are never Caveats (Kernel §9). The checkpoint stays at the last committed step.

## 10. Events (`runtime/events.py`)

```python
class NodeStarted(Model):     node: str
class NodeDone(Model):        node: str; notes: list[str]
class Token(Model):           node: str; text: str
class Reasoning(Model):       node: str; text: str
class ToolCalled(Model):      name: str; summary: str
class ToolReturned(Model):    name: str; summary: str
class ApiCalled(Model):       source: str; cached: bool; count: int; failed: bool = False
class ExtractProgress(Model): done: int; total: int
class Paused(Model):          pause: Pause
class Done(Model):            status: Literal["done", "aborted"]; paths: list[Path]
class Stopped(Model):         node: str | None; reason: str

RunEvent = Annotated[NodeStarted | ... | Stopped, Field(discriminator="type")]   # each has a Literal `type`
```

Pass 1 maps `NodeDone`, `Paused`, `Done` and `Stopped`. Pass 3 adds the rest. No event carries a branch ID.

| Event | Source | Rule |
|---|---|---|
| `NodeStarted` | `tasks` start | Once per stream for `batch_extract`, not once per branch |
| `NodeDone` | `updates` | `notes` are the messages of the `run_log` entries that node appended, found by diffing the log length. Skip the `__interrupt__` and `__metadata__` keys. For `batch_extract`, fires once, when `done == total`. |
| `Token` | `messages` | `AIMessage` from `fetch_agent` only, text blocks of `content_blocks` |
| `Reasoning` | `messages` | Reasoning blocks of `content_blocks`, from any node except `batch_extract`. Optional per turn: the view must cope with none. |
| `ToolCalled`, `ToolReturned`, `ApiCalled` | `custom` | Mapped from `{"type": ...}` dicts; see below |
| `ExtractProgress` | `tasks`, `updates` | `total` counts `batch_extract` task starts, `done` counts its `updates` chunks |
| `Paused` | `updates` | `__interrupt__` key |
| `Done`, `Stopped` | Controller | After the task ends |

**Extraction progress needs no signal from the stage.** Verified offline on the pinned versions with a 3-branch `Send`, one branch failing: all three `tasks` starts arrive before the first `updates` chunk, and on the rerun the finished branches still arrive as `updates` marked `cached`, but they have no `tasks` finish event. That makes `updates` the right count to use. The same run confirmed `tasks` mode leaves interrupts and `durability="sync"` working.

**Custom events.** `kernel/events.py` holds the guard:

```python
def emit(event: dict) -> None:
    try:
        get_stream_writer()(event)
    except RuntimeError:  # the Gateway and Tiers also run outside a graph, in tests and smokes
        pass
```

- The `tools` executor emits `{"type": "tool_called", "name", "summary"}` and `{"type": "tool_returned", ...}`, with summaries from [Collection LLD](collection.md) §5.
- The Gateway's `fetch` emits `{"type": "api_called", "source", "cached", "count", "failed"}` per source, after the `gather`. `cached` means `cache != miss`.
- Stages and the Gateway emit plain dicts, so they never import Runtime. The Controller maps them to `RunEvent` and drops unknown types with a log line.

**Known limits** (none needs code):
- Replay-cache hits give one whole message, not a typewriter effect, and identical hits may dedupe.
- Tokens from an attempt abandoned by a retry or fallback stay on screen, since they're never retracted. `Token` has no message ID, so the client can't replace them. The `NodeDone` that follows is what counts.

## 11. Lifecycle

`RunController.open`, closed in reverse:
1. Deps: `make_tiers`, `make_jev`, `async with make_gateway`.
2. Saver: raw `AsyncSqliteSaver(conn, serde=JsonPlusSerializer(allowed_msgpack_modules=[...]))` on `runs_db`, constructed inside the running loop. `from_conn_string` takes no `serde`. `setup()` is retried with backoff, because racing it on a fresh file fails.
3. Registry connection, on `runs_db` with a 5 s busy timeout. WAL comes from the saver's `setup()`.
4. `build_graph` compiles once.

The CLI opens one Controller per `asyncio.run`. Streamlit holds one on a background loop for the process lifetime.

## 12. CLI (`clients/cli.py`)

```
scout run "<request>" [--focus DIM ...]
scout resume [thread_id]
scout show <thread_id> [--log]
```

Stdlib `argparse` with `[project.scripts] scout = "talent_scout.clients.cli:main"`. `--focus` uses `action="append"` and `choices=` the `Dimension` values plus `salary`, an alias for `compensation` taken from the spec's example, and goes straight into `start(focus=...)`. A blank request is an argparse error.

**Prompts run outside the event loop.** `main` is a sync loop around `asyncio.run`, one per Controller:

```python
outcome = asyncio.run(drive_start(settings, request, focus))
while isinstance(outcome, Paused):
    answer = prompt(outcome.pause)                     # plain input()
    try:
        outcome = asyncio.run(drive_resume(settings, thread_id, answer))
    except InvalidAnswer as e:
        print_errors(e)                                # no state changed, so re-ask the same Pause
```

`input()` inside a running loop is what would break here: `asyncio.run`'s SIGINT handler only cancels the main task, so the first `Ctrl-C` wouldn't end a blocked `input()`. Outside the loop, `Ctrl-C` is a plain `KeyboardInterrupt`.

**Rendering** uses `rich` for output (spinner, dim reasoning, tables, Markdown) and `input()` for prompts.

| Pause | Shows | Takes |
|---|---|---|
| `clarify` | The questions and their options | An answer to each, in turn: a number picks that option, anything else is free text, Enter skips |
| `plan_review` | The Search Plan and Assumptions | One letter: approve / edit / reject (then asks for feedback) / abort |
| `low_data_review` | The counts, plans tried and any block reason | One choice: broaden (then optional guidance) / continue / abort |

- **Bad answers:** `InvalidAnswer` prints the errors and re-asks the same Pause, with no attempt cap.
- **`edit`:** writes the Search Plan as JSON to a temp file and opens `$EDITOR` (`notepad` as the Windows fallback). On save it validates against `SearchPlan`, and on an error re-opens the file with the error at the top.
- **`Ctrl-C` at a prompt:** the Run stays `paused`. Prints "resume with `scout resume <id>`" and exits 130.
- **`Ctrl-C` during a live Run:** `asyncio.run` cancels the driver, which awaits `handle.cancel()`, then prints "Stopped at <node>. Resume with `scout resume <id>`" and exits 130. There is no detach, because the Controller dies with the process. A second `Ctrl-C` kills it outright, which leaves a `running` row that reconcile fixes.

**`scout run`** prints progress, handles Pauses, and on `done` prints the Market Brief Markdown and both file paths. On `Stopped` it prints "Stopped at <node>: <reason>. Resume with `scout resume <id>`". Exit codes: 0 for `done` and `aborted`, 1 for `Stopped` or a refused call, 130 for `Ctrl-C`, 2 for argparse.

**`scout resume`.**
- No ID: a table of `paused` and `failed` Runs, newest first, with `#`, thread ID, status, summary, relative updated time, and a hint (pending Pause kind or stopped node). Prompts for a number or ID, first row on Enter. Prints "No resumable Runs" if empty.
- With an ID: `paused` re-shows its Pause. `failed` prints "Stopped at <node>: <error>. Retrying." and streams. `done` or `aborted` prints "Run already finished, see `scout show <id>`". `RunLocked` prints "This Run is open elsewhere".

**`scout show`.** Read-only. A header (ID, status, summary, updated time), then by status:
- `done`: the Market Brief Markdown and the `brief.md` path
- `paused`: the Pause, read-only, plus the resume hint
- `failed`: the stopped node, the error, and the resume hint
- `aborted`: the abort reason from `run_log`, or the row's error
- `--log` also prints `run_log` as a table.

**Progress, pass 1.** One line per `NodeDone`, raw node names, no labels: `✓ relevance — 38 of 142 Postings relevant (route: enough)`.

**Live view, pass 3.**

| Source | Shows |
|---|---|
| `fetch_agent` | Prose tokens, plus dim reasoning when it exists |
| Structured nodes (`clarity_check`, `plan`, `broaden`, `write_brief`) | Spinner "drafting <node>…", plus dim reasoning. JSON fragments are never shown, and there is no partial-field parsing. |
| `batch_extract` | Only a count: "extracted 37/142" |
| Tool and API calls | One line when called, one when done |
| Jev and plain-code nodes | Nothing beyond the `NodeDone` line |

The spinner stops on the first `Token` or `Reasoning` and restarts on the next `NodeStarted`, because raw text can't print under a `rich` live display.

## 13. Streamlit (pass 2)

Streamlit is thin and disposable: a simple web UI is future scope and will replace it. It gets no Controller changes and no event types of its own, and it renders a subset of what the CLI does.

- **Bridge (`streamlit_bridge.py`).** `st.cache_resource` holds a background thread running an event loop, with one `RunController` open on it. A sync wrapper calls it through `asyncio.run_coroutine_threadsafe`. A subscriber coroutine feeds a `queue.Queue` that the script reads.
- **Pages.** The thread ID lives in `st.query_params["thread"]`.
  - No ID: a request box, a focus multiselect, and a table of Runs linking to `?thread=<id>`.
  - With an ID: render from `get_run`. `paused` shows its form, `failed` shows the error and a Resume button, `done` shows the Brief with JSON and Markdown downloads.
- **Live view.** The handle sits in `st.session_state`. Node lines go in `st.status`, and from pass 3 tool and API lines too, with `st.progress` for extraction. Tokens and reasoning are ignored.
- **Pauses.** One `st.form` per kind, with a JSON `text_area` for `edit`. `InvalidAnswer` shows `st.error` above the same form.
- **Cut on purpose.** No re-attach, no Cancel button, no token placeholder. Reloading a running Run shows "Run in progress" with a Refresh button until it reaches a Pause or finishes. Closing the tab doesn't stop the Run, since the Controller owns the task.

## 14. Settings

Added to the Kernel's `Settings` (Kernel §13):

| Setting | Default |
|---|---|
| `runs_db` (path) | `.cache/runs.sqlite`, separate from `gateway_db`; locks live in `locks/` beside it |
| `runs_dir` (path) | `runs` |

## 15. Test seams and the skeleton proof

| Seam | Real | Fake |
|---|---|---|
| Stages | Each stage's `make_nodes`, `ROUTERS` | `stub_nodes()`, `STUB_ROUTERS` in `runtime/testing.py` |
| Deps | `make_tiers`, `make_jev`, `make_gateway` | `fake_deps(settings)`: fake chains, `fake_classifier`, `FakeGateway` |
| Balance | `check_balance` | Monkeypatched to pass |

**Stubs.** Each stub node writes one `log` note and a minimal valid slice for its owner (`render` writes `MarketBrief()` and a line of Markdown). The three Pause stubs each interrupt once. Stub routers walk one path: `clarity_check` → `clarify` until `questions` is non-empty, then `plan` → `plan_review` → `fetch_agent` → `collect` → `relevance` → `low_data_review` → `stats` → `write_brief` → `critic` → `render`.

**The proof, in `pytest`, with no LLM or network.** A test starts a Run in a subprocess and kills it with `taskkill /F` at each Pause. In a fresh process it fetches the typed Pause with `get_pause` and resumes, through all three Pauses to `done`. It also checks that a second process resuming a running thread gets `RunLocked`. Runtime is not done until this passes.

The clarify stub's payload holds real `ClarifyingQuestion`s, which carry a `StrEnum`. An enum inside a payload was untested in the research, so this test settles it. If it fails, store the field as `str`.

## 16. Build checklist

Each step leaves one small `pytest` file behind. No test calls an LLM or a jobs API.

**Pass 1 (walking skeleton):** wiring, SQLite, registry, Run Controller, Pause protocol, resume guard, CLI, stubs. `kernel/llm.py`'s streaming fixes are already in, with tests under `astream`.
1. Set `LANGGRAPH_STRICT_MSGPACK` in `__init__.py`. Add `rich` and pin `aiosqlite`. Add `runs_db` and `runs_dir`. Add `runs/` to `.gitignore`.
2. Stage `types.py` stubs, `runtime/pause.py`. Test: each Pause and answer survives a dump and load through the allowlisted serde, and `model_validate` rejects a bad answer.
3. `runtime/guard.py`. Test: a second subprocess is refused, and the lock frees after a kill.
4. `runtime/registry.py`. Test: `derive_status` for all five outcomes on a fake snapshot, and a transition updates `updated_at`.
5. `runtime/deps.py`, `runtime/testing.py`, `runtime/graph.py`. Test: the full graph compiles, and a stub Run reaches `render` with the expected Pauses.
6. `runtime/events.py` (pass 1 events), `runtime/controller.py`. Test: `start`, `resume`, `get_pause`, `get_run`, `list_runs`; each refusal changes nothing; a raising node gives `failed`, `Stopped`, and resumes rerunning only that node; `cancel()` gives a resumable `failed`; a stale `running` row reconciles; closing a subscriber doesn't stop the Run; `done` writes both files, and reconcile writes them too.
7. The skeleton proof (§15).
8. `clients/pauses.py`, `clients/cli.py`. Test: scripted `input` drives `scout run` through the stub Pauses; a bad answer re-asks; `resume` and `show` output per status. Check `Ctrl-C` by hand on Windows, in both places.
9. One live smoke script (not in CI): the same flow with the real `check_balance`.

**Pass 2:**
1. `--focus` through to `State.focus`. Test: the value is in the checkpoint.
2. Add the `streamlit` group, `streamlit_bridge.py`, `streamlit_app.py`. Check by hand through a stub Run: start, each Pause form, a bad answer, reload at a Pause, and download. No automated tests: the page is disposable.

**Pass 3 (event stream):**
1. `kernel/events.py`. Test: a no-op outside a graph, delivered inside one and through `owned()`.
2. Emit from the `tools` executor ([Collection LLD](collection.md) §14) and the Gateway's `fetch`. Test: the real Gateway on a mock transport, inside a one-node graph, emits one `api_called` per source, including a failed one.
3. The rest of the mapping in `runtime/events.py`. Test on a scripted graph: tokens only from `fetch_agent`, reasoning optional, `Token` and `Reasoning` absent from the replay buffer, and a `Send` run with one failure counts correctly across the rerun, with `NodeDone` firing once.
4. CLI live view (§12) and Streamlit's tool and API lines. One live run to check how the view reads, and check whether `deepseek/deepseek-v4.1-flash` sends readable reasoning, which research didn't test.

**Pass 6:** `AsyncSqliteStore` on `runs_db` on its own connection, with values written using `model_dump(mode="json")` and read with `model_validate` (⏳ Long-term memory).

## 17. Excluded and deferred

- Deliberate deferrals are in [future-scope.md](future-scope.md).
- Handed on:
  - ⏳ **Analysis:** `fan_out(state)` (§4).
  - ⏳ **Brief:** `critic` pass-through until pass 5. `done` depends on `render` writing `brief`.
  - ⏳ **Long-term memory:** opening the Store.
  - ⏳ **Infra shell:** the API and workers wrap `RunController`. A worker owning the task is what would make a client detach possible.
