# Web UI LLD

The low-level design of the browser client (part of component H in [HLD](../HLD.md) §3), precise enough to build from. It replaces Streamlit. Deliberate deferrals live in [future-scope.md](future-scope.md). The Run Controller, events and Pauses it sits on are in the [Runtime and Clients LLD](runtime.md).

Source tickets (each holds the full reasoning, and what was verified):
- [Research: delivering Run events over FastAPI SSE](../../.scratch/web-ui/issues/01-research-sse-over-fastapi.md)
- [Research: graph rendering and GSAP in React](../../.scratch/web-ui/issues/02-research-graph-rendering-and-gsap.md)
- [Web API and hosting](../../.scratch/web-ui/issues/03-web-api-and-hosting.md)
- [App shell and history sidebar](../../.scratch/web-ui/issues/04-app-shell-and-history-sidebar.md), with [its prototype](../../.scratch/web-ui/prototype/shell/index.html)
- [Trace graph](../../.scratch/web-ui/issues/05-trace-graph.md), with [its prototype](../../.scratch/web-ui/prototype/trace/index.html)
- [Live Run view](../../.scratch/web-ui/issues/06-live-run-view.md)
- [Pause forms](../../.scratch/web-ui/issues/07-pause-forms.md)
- [Brief view](../../.scratch/web-ui/issues/08-brief-view.md)
- [Motion with GSAP](../../.scratch/web-ui/issues/09-motion-with-gsap.md)
- [Frontend build and verification](../../.scratch/web-ui/issues/10-frontend-build-and-verification.md)

## 1. What it is

A user starts a Run, watches it live (streamed tokens, tool-call loading states, a trace graph with animated progress), answers Pauses, reads the Market Brief, and finds every earlier Run in a chat-style sidebar.

Two parts, in one process on one port:
- `clients/web.py`: a FastAPI app hosting one `RunController` for the process lifetime. It only adapts the Controller and adds no Run logic.
- `web/`: a Vite, React and TypeScript single-page app, built to static files FastAPI serves. GSAP does all animation.

It does **not** include a queue, workers, auth, multi-user, or deployment (Infra shell). A browser can close and reopen without stopping a Run, because the Controller lives in the server. A server restart behaves as a CLI exit does: the Run is `failed` and resumable.

It does not own what each Pause asks, what `focus` changes, or node bodies (stage LLDs), or any preferences UI (Long-term memory). There is no deleting, renaming or searching of Runs.

## 2. Layout

```
src/talent_scout/
  clients/web.py           # the app: endpoints, RunDetail, guards, static files
  clients/cli.py           # gains `scout serve`
  runtime/demo.py          # demo_nodes, DEMO_ROUTERS, demo_brief
  runtime/controller.py    # the changes in §3
  runtime/graph.py         # gains graph_topology(); overlays the demo graph
web/
  package.json  package-lock.json  index.html  vite.config.ts  tsconfig.json
  src/
    main.tsx  App.tsx  router.ts  styles.css  motion.ts
    api/      client.ts  stream.ts  types.ts
    run/      steps.ts  reducer.ts  fromLog.ts  useRun.ts  RunPage.tsx  Stream.tsx  Turn.tsx  ToolCard.tsx
    pause/    PauseCard.tsx  ClarifyForm.tsx  PlanReviewForm.tsx  PlanEditor.tsx  LowDataForm.tsx
    brief/    BriefView.tsx  Evidence.tsx  RunNotes.tsx
    trace/    TracePanel.tsx  TraceStep.tsx  ProgressBar.tsx  StageStrip.tsx
    sidebar/  Sidebar.tsx  useRuns.ts
    composer/ Composer.tsx
    test/     reducer.test.ts  steps.test.ts  demo-run.json
scripts/smoke_web.py
tests/test_web_api.py
```

**Dependencies.**
- Python: `fastapi==0.162.0` and `uvicorn==0.54.0` in the main `dependencies`. `uv run` only includes `dev` by default, so a group would break a plain `uv run scout serve`.
- npm, exact versions with a committed lockfile: `react` and `react-dom` 19.3.1, `gsap` 3.15.0, `@gsap/react` 2.1.2; dev: `vite` 8.3.5, `@vitejs/plugin-react` 6.1.2, `typescript` 7.0.2, `vitest` 5.0.5, `@types/react` and `@types/react-dom` 19.3.0.
- **Deliberately none:** router (about 15 lines over `pushState`), state library (`useReducer`), CSS framework, graph or layout library, Markdown renderer, generated API types.
- All GSAP plugins are free under its Standard licence. The pinned set builds to 106.7 kB gzip.

`.gitignore` adds `web/node_modules/` and `web/dist/`.

## 3. Controller changes

The only ones. The API needs nothing else from Runtime.

```python
class RunHandle:
    def __init__(self, thread_id: str, log_start: int): ...   # the log_len _spawn already receives
    @property
    def buffered(self) -> int: return len(self._buffer)

class RunController:
    self._live: dict[str, RunHandle]                          # was a set
    def attached(self, thread_id: str) -> RunHandle | None: ...
    def brief_paths(self, thread_id: str) -> list[Path]: ...  # was _brief_paths
```

- `attached` is re-attach. `events()` already supports several subscribers and replays the buffer.
- `check_balance` is skipped when `settings.demo`, as it already is under `replay_cache`.
- `open_deps` yields `fake_deps` with `demo=True` when `settings.demo`. `Deps` gains `demo: bool = False`.
- `build_graph` overlays `demo_nodes()` and `DEMO_ROUTERS` when `deps.demo`.
- `runtime/graph.py` gains `graph_topology()`, returning `{nodes: [{id, owner}], edges: [{source, target}]}` from `OWNERS`, `EDGES` and `CONDITIONAL`, in `OWNERS` order.
- `ALLOWED_MSGPACK` gains `HiringRequest`, `LogKind`, `RunLogEntry`, `ClarifyingQuestion`, `SearchPlan` and `MarketStats`. Each load logs a "Blocked deserialization" line for them today. It's harmless, since `State.model_validate` copes, but it would fill a long-lived server's log.

Settings: `demo: bool = False`, `demo_delay: float = 0.4`.

## 4. Web API (`clients/web.py`)

All under `/api`. **Every path op is `async def`:** a sync one runs on a thread pool, and the lock connection and `aiosqlite` belong to the loop thread.

| Method, path | Body | Success | Refusals |
|---|---|---|---|
| `GET /meta` | | `{graph, dimensions, countries, categories, confidence_key, demo}` | |
| `GET /runs` | | `list[RunRecord]`, newest first | |
| `POST /runs` | `{request_text: NonBlank, focus: list[Dimension] = []}` | 201 `{thread_id}` | 402, 502, 422 |
| `GET /runs/{id}` | | `RunDetail` | 404 |
| `POST /runs/{id}/resume` | `{answer: dict or null}` | 200 `{thread_id}` | 404, 409, 422, 402, 502 |
| `POST /runs/{id}/cancel` | | 200 `Stopped` | 404, 409 |
| `GET /runs/{id}/events` | | 200 SSE, or 204 when nothing is live here | 404 |
| `GET /runs/{id}/brief.json`, `brief.md` | | the file, as a download | 404 |

`countries` is `sorted(ADZUNA_CURRENCY)`, `categories` is `sorted(ADZUNA_CATEGORIES)`, `confidence_key` is `CONFIDENCE_KEY`. The API exposes no JSON Schema, since the UI renders three typed Pause kinds.

**Refusals** share one body, `{code, message, errors?}`:

| Code | Status | From |
|---|---|---|
| `unknown_run` | 404 | `UnknownRun` |
| `no_brief` | 404 | a brief download on a Run with no Brief |
| `run_locked` | 409 | `RunLocked` |
| `not_resumable` | 409 | `NotResumable` |
| `not_live` | 409 | cancel with no attached handle |
| `invalid_answer` | 422 | `InvalidAnswer`, with `errors: [{loc, msg}]` |
| `invalid_request` | 422 | FastAPI's validation errors, reshaped by one handler |
| `balance_too_low` | 402 | `BalanceTooLow` |
| `upstream` | 502 | `httpx.HTTPError` from `check_balance` |

**`InvalidAnswer` must be cleaned.** Pydantic's raw errors hold exception objects in `ctx`, which JSON can't carry. Send only `loc` and `msg`, with the "Value error, " prefix stripped. A field error has `loc: ["plan", "radius_km"]`, and a model-level one has `loc: []`.

**`RunDetail`, not `RunView`,** because `state` holds LangChain messages and every Posting's full text:

```python
class LogLine(Model):
    node: str; kind: LogKind; message: str

class PostingRef(Model):
    key: str; title: str; company: str | None; location: str; url: str | None; posted_at: date

class RunDetail(Model):
    record: RunRecord
    request_text: str | None   # None before the first checkpoint; the UI falls back to record.summary
    focus: list[Dimension]
    pause: Pause | None
    stopped_at: str | None
    run_log: list[LogLine]
    live_from: int | None      # handle.log_start of the attached handle; None if none is attached here
    brief: MarketBrief | None
    sample: list[PostingRef]   # empty unless there is a Brief
```

`PostingRef.url` is null unless the scheme is http or https, the same guard as `brief/markdown.py`'s `_link`. Read `attached` straight after `await get_run`, with no await between, so `live_from` names the current handle.

### Event stream

`EventSource` on GET, with FastAPI's `EventSourceResponse`, which sets the headers and sends a `: ping` after 15 s idle. One unnamed message per event, with `data` the event's `model_dump_json()`, so `RunEvent` goes out unchanged. No `event:` names or `id:` lines.

```python
async def live_handle(thread_id: str, request: Request) -> RunHandle:
    controller = request.app.state.controller
    await controller.get_pause(thread_id)  # UnknownRun becomes 404
    handle = controller.attached(thread_id)
    if handle is None:
        raise HTTPException(204)  # EventSource's documented stop signal: closed, with no retry
    return handle

@api.get("/runs/{thread_id}/events", response_class=EventSourceResponse)
async def events(handle: Annotated[RunHandle, Depends(live_handle)]) -> AsyncIterator[ServerSentEvent]:
    replay = handle.buffered  # no await before events() takes its snapshot, so the count is exact
    if replay == 0:
        yield CAUGHT_UP
    sent = 0
    async for event in handle.events():
        yield ServerSentEvent(raw_data=event.model_dump_json())
        sent += 1
        if sent == replay:
            yield CAUGHT_UP
```

- **`{"type": "caught_up"}`** is the one synthetic message, and isn't a `RunEvent`. It marks the end of the replay. `Token` and `Reasoning` are queue-only, so none comes before it.
- **Disconnect needs no code.** `events()`'s `finally` drops the subscriber and the Run is untouched. Never wrap it in `asyncio.wait_for`: a timeout kills the generator.
- **The client must `close()` on `Paused`, `Done` and `Stopped`.** Otherwise a stream that ends normally reconnects and replays forever.
- **The status row lags the event.** `Paused` is published from inside the graph stream, before the task ends, so right after it `GET /runs/{id}` can still say `running` with a live handle. Trust the event (§7).
- **One stream per open Run page,** and none for the sidebar: browsers allow about 6 connections per origin over HTTP/1.1, across tabs.

### Local security

The server has no auth and can spend quota, and any web page can send requests to localhost.

- Binds `127.0.0.1`, with no `--host` flag.
- `TrustedHostMiddleware(allowed_hosts=["127.0.0.1", "localhost"])` stops DNS rebinding.
- `same_origin`, a dependency on every POST: if `Origin` is present and the part after `://` differs from `Host`, 403. This also covers a body-less cross-origin cancel, which content-type checks would miss.
- No `BaseHTTPMiddleware`, so nothing sits between the SSE response and disconnect handling.

### Hosting

```python
@asynccontextmanager
async def lifespan(app):
    async with RunController.open(app.state.settings) as controller:
        app.state.controller = controller
        yield
```

`scout serve [--port 8000] [--demo]` imports `clients/web.py` lazily, so other commands don't load FastAPI, and calls `uvicorn.run(app, host="127.0.0.1", port=port, timeout_graceful_shutdown=3)`.

- `timeout_graceful_shutdown` is required: on Windows a shutdown with an open stream otherwise hangs. Lifespan exit then cancels live Runs through the existing `open()`, leaving them `failed`, `cancelled` and resumable.
- One worker and no `--reload`, because a reload would stop live Runs.
- `/assets` is mounted from `web/dist/assets`. A catch-all GET returns `index.html`, so `/runs/:id` survives a reload, and `/api/*` stays a real 404. With no `web/dist`, the catch-all says to run the build.
- Concurrent Runs have no limit. They share one Gateway, whose daily budget counter is atomic, so the first come is served first.

### Demo mode

`--demo` builds settings with `make_settings(demo=True, runs_db=".cache/demo/runs.sqlite", runs_dir=".cache/demo/runs")`, so it needs no `.env` and demo Runs never reach real history. Bare stubs emit no tokens, tools or delays, so `runtime/demo.py` overlays paced nodes, sleeping `demo_delay` each, on one scripted path:

| Part | What it exercises |
|---|---|
| `clarity_check` then `clarify` | `Reasoning`, a question with options |
| `plan` then `plan_review` | `Reasoning`; honours approve, edit, reject and abort |
| `fetch_agent` and `tools`, twice | `Token`, `ToolCalled`, `ApiCalled`, `ToolReturned`, one source cached |
| `relevance` then `low_data_review` | The low-data Pause, on the first Attempt only; honours all three actions |
| `broaden` | A loop back to Search |
| `batch_extract`, 6 `Send`s | `ExtractProgress` |
| `write_brief`, `critic` twice | `Reasoning`, and the critic back-edge once |
| `render` | `demo_brief()`: all recommendations, each Confidence, Caveats, real `render_markdown` output |

- Tokens come from a small `BaseChatModel` scripted with `_astream`, yielding `AIMessageChunk`s with `reasoning` and `text` blocks, called with `ainvoke`. `messages` mode picks them up as it does a real model.
- A request containing "fail" raises once in `normalise_skills`, to exercise `Stopped` and Resume.

## 5. Shell

Left: sidebar, 272 px. Centre: one column, max 740 px, holding the request bubble, the stream, the Pause card, then the Brief. Right: trace panel, 316 px, on an opened Run only.

Under about 900 px, the sidebar becomes a slide-over from a header button that shows how many Runs need the user, and the trace panel becomes a one-line strip (§6).

**Routes.** `/` is the composer and `/runs/:id` an opened Run. Start navigates once the API returns the thread ID. An unknown ID shows "Run not found" with a link to `/`.

**Sidebar.** Product name, New Run, then:
- **Needs you**, pinned and shown only when non-empty: every `paused` and `failed` Run, newest first, bold, and not repeated below.
- `running` and finished Runs under Today, Yesterday, Previous 7 days and Earlier, by calendar day of `updated_at` in the browser's timezone.
- A row is the title (`record.summary`, one line, ellipsised by CSS), a status badge and a relative time.

| Status | Badge | Colour |
|---|---|---|
| `running` | Running, pulsing dot | Blue |
| `paused` | Needs you | Amber |
| `failed` | Stopped | Red |
| `done` | Done | Green |
| `aborted` | Aborted | Grey |

**How the sidebar learns of changes.** It polls `GET /runs` every 3 s while any row is `running` and every 15 s otherwise, plus on window focus and after the user starts, resumes, cancels or answers. A stream's terminal event triggers one refetch after 300 ms, because the row lags the event. When the open Run's `status` or `updated_at` differs from what the page last saw, and the page holds no stream, the page refetches `RunDetail` and re-attaches.

**Composer.** A centred heading, a textarea, the five Dimensions as toggle chips (Demand, Compensation, Skills, Competition, Titles & seniority) and Start. The CLI's `salary` alias isn't offered, since the Compensation chip is the same Dimension. Enter submits, Shift-Enter adds a line, and a blank request can't be submitted.

**What an opened Run shows first.**

| Status | Shows |
|---|---|
| `running`, live here | Request, history from `run_log`, then the attached stream |
| `running`, not live here | Request, history, "Running in another window", polling every 3 s |
| `paused` | Request, history, Pause card |
| `failed` | Request, history, the Stopped banner with Resume |
| `aborted` | Request, reason, history, no Brief |
| `done` | Request, closed "How this Run went", then the Brief |

Colours are custom properties on `:root`, lifted from the shell prototype. Light only.

## 6. Trace panel

**14 Steps in four bands, not 17 raw nodes.** `run/steps.ts` holds the label table. A Step's label stays in the UI, while topology comes from `/meta`.

| Band | Step (id: label) | Raw nodes | Weight |
|---|---|---|---|
| Understand | `read`: Read your request | `intake`, `clarity_check` | 1 |
| | `ask`: Ask you | `clarify` | optional, Pause |
| | `plan`: Plan the search | `plan` | 1 |
| | `approve`: Your approval | `plan_review` | 0.5, Pause |
| Collect | `search`: Search job boards | `fetch_agent`, `tools` | 3 |
| | `filter`: Filter postings | `collect`, `relevance` | 1 |
| | `widen`: Widen the search | `broaden` | optional |
| | `few`: Too few postings? | `low_data_review` | optional, Pause |
| Analyse | `postings`: Read postings | `batch_extract` | 4 |
| | `normalise`: Tidy skill names | `normalise_skills` | 1 |
| | `stats`: Compute the numbers | `stats` | 1 |
| Brief | `write`: Write the brief | `write_brief` | 2 |
| | `check`: Check every claim | `critic` | 1 |
| | `finish`: Finish | `render` | 0.5 |

Steps are ordered by owner band, then node order, from `/meta`. Edges map through the table, dropping self-edges and `START`/`END`. An edge to an earlier Step is a back-edge. This must yield exactly `ask→read`, `approve→plan`, `widen→search`, `few→widen`, `check→write`, and a node missing from the table fails a test, so a new node can't go unlabelled.

**Layout: hand-written SVG on a fixed vertical rail,** with one 214 px node per Step and 22 px between them. Only back-edges are drawn as edges, bowed to the right. Rail segments carry forward progress. A forward edge that skips a Step isn't drawn: the skipped Step says "Not needed". The Search node is taller and holds source pills. The panel scrolls and keeps the live Step in view. Clicking a waiting Step scrolls to its Pause card.

**States, each readable without colour:**

| State | Looks like |
|---|---|
| idle | Hollow circle. Optional Steps have a dashed outline from the start |
| active | Spinner arc, pulsing ring, flowing rail |
| done | Filled green circle with a drawn check |
| waiting | Amber, pause bars, slow ring, "Waiting for you to approve" and so on |
| failed | Red cross, "Stopped. Resume retries it" |
| skipped | Faded, dashed, "Not needed" |

A Step is done when the Run moves to a different Step, or on `Done`. A Pause only marks its own Step waiting.

**Tools and API calls** show on the Search Step, not as nodes. While a call is in flight its line reads `Adzuna · "data engineer" page 1`. A source pill shows the count (filled blue), "· cached" (hollow), or a cross (red). `search_adzuna` and `adzuna` map to Adzuna, `search_usajobs` and `usajobs` to USAJOBS, and an unknown name shows raw.

**Loops.** A Step that runs again gets a badge ("×2"), the back-edge turns amber and a dot travels along it. Steps between the target and where the Run was reset to idle with their notes cleared, except optional Steps that ran, which stay done.

**Fan-out.** `batch_extract` is one Step with a bar and "3 of 6 batches", since no event carries a branch ID.

**Progress bar.** A Step's share is its weight over the total weight. An active Step counts 35% of its weight (`postings` counts its batch fraction), and a done Step counts all of it. `Done` snaps to 100%, and the value never decreases: `progress = max(previous, computed)`. Amber while waiting, red on `Stopped`. A line under it names the live Step ("Search job boards…", "Waiting for you: Your approval", "Stopped at …").

**Narrow screens.** The same state as four band chips (done, active, waiting or failed), the live-Step line and the bar.

## 7. Live view

**A turn is one visit to one Step.** A `NodeStarted` whose Step differs from the current turn's opens a new turn, so `fetch_agent` and `tools` stay in one turn, and a loop opens another. The stream is the chronological record, and the trace is the map. The active turn is expanded. A finished one collapses to its check, label and last note, and expands on click. Once a Run is `done`, all turns fold under a closed "How this Run went".

| Event | Effect on the stream |
|---|---|
| `NodeStarted` | New turn if the Step changed; a `drafting` line for the nodes below |
| `Reasoning` | Appends to a `thinking` block, a closed `<details>` reading "Thinking…" then "Thought", body dimmed. Created on the first fragment, so none means no block |
| `Token` | Appends to a `prose` block, plain text with `white-space: pre-wrap`; ends the drafting line |
| `ToolCalled` | Opens a `tool` card: spinner, source name, summary |
| `ApiCalled` | Sets the source pill on the first card named `search_<source>` without one, else a turn-level pill |
| `ToolReturned` | Resolves the oldest open card of that name: check, then the summary |
| `ExtractProgress` | The turn's `progress` bar and "3 of 6 batches" |
| `NodeDone` | Appends notes; ends the drafting line |
| `Paused` | The Pause card, inline at the end of the stream |
| `Done`, `Stopped` | Endings, below |
| `caught_up` | `animate: true`; adds a `gap` line if needed |

**Drafting phrases.** `clarity_check` "Working out what's unclear…", `plan` "Drafting the search plan…", `broaden` "Working out how to widen the search…", `write_brief` "Drafting the brief…", `critic` "Checking claims against the numbers…". JSON fragments are never shown. A card still open at `Stopped` reads "Interrupted". Tools pair first-in-first-out by name: `tools` runs calls in a `gather` but emits `tool_returned` in call order.

### State

```ts
type RunState = {
  turns: Turn[]
  trace: TraceState            // the prototype's reducer, in TypeScript
  pause: Pause | null
  ending: Ending | null
  connection: "live" | "reconnecting" | "closed"
  animate: boolean             // false until caught_up, and on any reopened Run
}
const reduce = (state: RunState, event: WireEvent): RunState => ...
```

The reducer is pure. **Batching:** `useRun` pushes events onto a queue flushed once per frame (`requestAnimationFrame`, with a 250 ms timeout because frames stop in a hidden tab), and folds the batch in one dispatch. One render per frame carries any token rate, and a replay settles at once. Finished turns are `memo`ised.

**`fromLog(detail)`** builds a starting state with no stored events. It groups `run_log[:live_from]` (or all of it, with no live handle) into turns by consecutive Step, and counts each Step's groups as its visits. Three nodes write no log line in normal use, so it infers them: a `collect` line means `search` ran before it, and a `normalise_skills` line means `postings` ran before it. Then it places the cursor from `record.status`, `pause` and `stopped_at`. A reopened Run keeps its route, counts and notes, and loses tokens and tool cards.

### Connecting

Each stream has a `base` state, and **`onopen` resets to `base`**, because a replay starts at the current handle's start, and `run_log[:live_from]` is exactly what comes before it, with no overlap and no race.

| How the stream opened | `base` |
|---|---|
| A new Run | Empty |
| Page load or reload | `fromLog(detail)` |
| After answering a Pause or pressing Resume | The state on screen, with the Pause marked answered |

Marking it answered is a local action: the rerun Pause node's `NodeStarted` wouldn't otherwise take its Step out of waiting.

**Text survives a reconnect.** Live text sits in a `texts` map keyed by turn index, which `onopen` doesn't reset. Replays are deterministic, so indices line up. Text sent during an outage is lost, so `caught_up` adds one muted line, "Some live text wasn't kept", when the active turn could have streamed and was reached by replay.

**`error` events.** With `readyState` 0 (reconnecting), after a 2 s grace, a "Reconnecting…" pill shows at the end of the stream. With `readyState` 2 (204 or 404), fetch `RunDetail` and rebuild, which also covers a server restart mid-Run.

### Endings

The client calls `close()` on every terminal event, and trusts it rather than refetching to confirm.

- **`Paused`:** the card renders from the event's own payload.
- **`Done`, `done`:** fetch `RunDetail`, retrying up to 5 times at 200 ms while it says `running`, then show the Brief.
- **`Done`, `aborted`:** "This Run ended without a Brief", the reason (the last `run_log` message or `record.error`, as `scout show` does), and a link to `/`.
- **`Stopped`, with a node:** "Stopped at <Step>. Nothing is lost; Resume retries that step", Resume (`answer: null`), and the raw reason in a `<details>`. With reason `cancelled`, "You stopped this Run at <Step>".
- **`Stopped`, `node: null`:** nothing was checkpointed, so no Resume, only a link to `/`.

**Stop.** While a Run is live here, the Run header has a Stop button with no confirmation, since Resume undoes it.

**Auto-scroll.** The stream sticks to the bottom while a sentinel at the end is within 80 px of view (`IntersectionObserver`). Scrolling up unsticks it and shows a "Jump to latest" pill, which reads "Waiting for you" when a Pause arrived off-screen. The scroll write happens once per flush.

**Accessibility.** The stream is `role="log"` with `aria-live="off"`, since announcing every token would be unusable. A visually hidden `aria-live="polite"` region announces Step changes, Pauses and endings. A Pause heading takes focus on arrival when the stream is stuck to the bottom.

## 8. Pause cards

Every card posts `{answer: <payload>}` to `resume`. `PlanReviewAnswer` has no defaults and forbids extras, so all its keys are always sent.

| Kind | Action | `answer` |
|---|---|---|
| `clarify` | Send | `{answers: string[]}`, one per question in order, `""` for a skipped one |
| `plan_review` | Approve | `{action: "approve", plan: null, feedback: null}` |
| | Edit | `{action: "edit", plan: <SearchPlan>, feedback: null}` |
| | Reject | `{action: "reject", plan: null, feedback: "<text>"}` |
| | Abort | `{action: "abort", plan: null, feedback: null}` |
| `low_data_review` | Search wider | `{action: "broaden", guidance: "<trimmed>" or null}` |
| | Continue | `{action: "continue", guidance: null}` |
| | Abort | `{action: "abort", guidance: null}` |

**`clarify`, "A quick question" or "A few quick questions".** Each question has its text, `options` as real radio inputs styled as chips, and a free-text box. Picking a chip fills the box, and typing clears the chip. The button reads "Send answers", or "Continue without answering" when all are blank.

**`plan_review`, "Check the search plan".** Titles as chips, Where (`location` or "Country-wide", country code in capitals), Radius, Posted within N days, Target N Postings, Category (or "Any"), then Assumptions as "seniority: Senior, because …". Actions: Approve (primary), Edit, Ask for a different plan (a required feedback box), Abort.

**`PlanEditor` is a structured form,** not the CLI's JSON editor:

| Field | Control |
|---|---|
| `titles` | 1 to 4 text rows, add and remove |
| `country` | Select from `/meta` `countries` |
| `location` | Text; blank means country-wide |
| `radius_km`, `max_days_old`, `target_postings` | Number inputs, 0 to 100, 1 to 60, 20 to 200 |
| `category` | Select from `/meta` `categories`, plus "Any" (null) |

HTML limits only help, and the server stays the check. "Use this plan" submits.

**`low_data_review`, "Too few Postings".** "Only 3 relevant Postings found; the target is 20." "Fetched 50, rejected 47 as not the role, over 1 Attempt." Then `blocked` if set, Adzuna calls left if known, and the plans tried in a `<details>`. An optional guidance box feeds Search wider. Then "Continue with 3 Postings" and Abort.

**Abort is two-step everywhere,** an inline "Abort this Run? Yes / No", because it's the one irreversible answer.

**Refusals, with values kept and no state changed.**

| Refusal | Shows |
|---|---|
| `invalid_answer` | `loc[0] === "plan"` under the field named by `loc[1]`; anything else at the top of the card |
| `invalid_answer` saying the Run isn't waiting, or `not_resumable` | "Answered elsewhere", then refetch and rebuild |
| `run_locked` | Retry once after 300 ms, then "This Run is open elsewhere" |
| `balance_too_low`, `upstream` | The message at the top; the Run stays `paused`, so it can be retried |

**After answering,** the card collapses to a one-line record ("You approved the plan", "You answered 2 questions"), and the new stream opens. On a reload the record is the raw message of the `pause` entry in `run_log`. A `paused` Run reopened from the sidebar renders its card from `RunDetail.pause`, identical to a live one.

A stale card in a second tab lasts at most one sidebar poll. A stale answer can only pass if the Run is at a later Pause of the same kind, which needs a reject loop plus a second tab, and that is accepted.

`clients/pauses.py` stays for the CLI alone.

## 9. Brief view

Rendered from `RunDetail.brief` and `sample`, not `brief.md`: Evidence needs to expand, and with no Markdown renderer or raw HTML, outside text stays escaped by React. Section order is `brief.md`'s, so screen, download and print agree.

| # | Section | Component | Reads |
|---|---|---|---|
| 1 | Title, Download JSON, Download Markdown, Print | `BriefHeader` | `hiring_request.role`, `.location` |
| 2 | Replay banner, Weak Sample notice | `BriefNotices` | `replayed`; `stats.sample_size < run_notes.final_plan.target_postings` |
| 3 | Summary | `Summary` | `summary` |
| 4 | Hiring Outlook | `Outlook` | `outlook` |
| 5 | Client Recommendations | `Recommendations` | `recommendations` |
| 6 | Insights | `Insights` | `insights`; `/meta` `confidence_key` in a closed `<details>` |
| 7 | Run Notes | `RunNotes` | `run_notes` |
| 8 | Postings analysed | `PostingsTable`, closed `<details>` | `sample` |

Notice and empty-state wording matches `brief/markdown.py`.

**Never colour alone.**
- Confidence Tag: a pill with the word and a meter (●●● High, ●●○ Medium, ●○○ Low), and `confidence_reason` beneath.
- Hiring Outlook: a large word with a shape, ▲ Favourable, ◆ Competitive, ▼ Hard to fill, then `reason`.
- Caveat: a warning icon and the word "Caveat" on each.

**Run Notes stay open,** with Caveats first, since a closed fold would hide what most affects trust. Then Questions and answers, Assumptions, Focus, Final Search Plan, earlier plans, Postings analysed by source (from `posting_keys` prefixes), source match counts, attribution.

**`Evidence`,** used by Insights, Recommendations and the Outlook. "Evidence: 38 Postings" expands inline to the cited Stats (`stat_ids` in `brief.stats`: label, value, unit) and the Postings (`posting_keys` in `sample`: title and company, ten at first, then "Show all 38"). Links use `target="_blank" rel="noopener noreferrer"`, and a null `url` shows no link.

- `Evidence.count` is a Python property and isn't in the JSON, so use `posting_keys.length`.
- An Outlook with empty `stat_ids` is the default and shows no Evidence.
- A salary band reads `low to high unit`, with no decimals, via `toLocaleString`.

**Print is a stylesheet only.** `@media print` hides the sidebar, trace panel, "How this Run went" and all buttons, and widens the column. Closed `<details>` stay closed, so the full Posting list belongs to the Markdown download.

## 10. Motion

**The one rule: React renders the final state, and GSAP only plays the way into it.** Classes and attributes carry every state, so tweens are `from` or decorative. Reduced motion is then simply no tweens, a replay can't play back steps, and with `animate: false` no one-shot fires.

```ts
// motion.ts: registers useGSAP, DrawSVGPlugin and MotionPathPlugin once
export const DUR = { fast: 0.15, base: 0.25, slow: 0.5 }
export const EASE = { out: "power2.out", pop: "back.out(3)", linear: "none", settle: "elastic.out(1.2,0.3)" }

export function useMotion(fn: () => void, deps: unknown[], scope: RefObject<Element>) {
  useGSAP(() => {
    gsap.matchMedia().add("(prefers-reduced-motion: no-preference)", fn)
  }, { dependencies: deps, scope, revertOnUpdate: true })
}
```

Each animated component owns one call, so a loop ends itself when its state changes. Handlers use `contextSafe`. Previous state comes from a ref, to tell an entry from a re-render.

| Trigger | Target | Tween | Duration, ease |
|---|---|---|---|
| Step active | Icon arc | rotate 360, repeating | 0.9 s, linear |
| | Ring | opacity .55 to 0, scale 1 to 1.04, repeating | 1.3 s, out |
| Rail segment live | `stroke-dashoffset` | 10 to 0, repeating | 0.6 s, linear |
| Step done | Check path | `drawSVG` 0 to 100% | 0.35 s, out |
| Step waiting | Ring | opacity .6 to 0, scale 1 to 1.05, repeating | 2 s, sine.out |
| Step failed | Group | x -3 to 0 | slow, settle |
| Counter changes | Badge | scale 1.6 to 1 | 0.4 s, pop |
| Loop taken | Dot on the back-edge | `motionPath` 0 to 1, then hidden | 0.9 s, power1.inOut |
| Progress changes | Overall bar | `scaleX`, origin left | slow, out |
| `ExtractProgress` | Turn's and Step's bars | `scaleX` | base, out |
| New turn | Turn | y 6 to 0, opacity 0 to 1 | base, out |
| Tool card enters | Card | y 4 to 0, opacity 0 to 1 | fast, out |
| Tool card resolves | Check path | `drawSVG` 0 to 100% | 0.35 s, out |
| Prose streaming | Caret | opacity 1 to 0, repeating | slow, stepped |
| Sidebar row `running` | Badge dot | opacity 1 to .25, scale to .7, repeating | 0.6 s, sine.inOut |
| New sidebar row | Row | opacity 0 to 1 | base, out |
| Row status changes | Badge | opacity 0 to 1 | base, out |
| Pause card arrives | Card | y 8 to 0, opacity, then border pulse twice | base, out |
| Brief arrives live | Sections | y 8 to 0, opacity, stagger .06 | base, out |

**Budget.**
- **No per-token tween.** Text is appended per frame, and the caret is the only motion on prose.
- Only `transform`, `opacity` and SVG attributes tween, never layout. `<details>` opens instantly.
- The repeating tweens at any moment are the active Step's three, one caret, and one dot per `running` row.
- One-shots on the stream fire per turn or per card. At most one loop dot plays per batch.

**Scrolling** is native `scrollIntoView({behavior: "smooth", block: "nearest"})`, `"auto"` under reduced motion. **Off-screen:** below 900 px the panel isn't mounted, so its loops don't exist, and a hidden tab costs nothing because GSAP's ticker follows `requestAnimationFrame`.

**Reduced motion leaves** static icons, final colours, instantly set bars, the counter and instant scrolling, with no repeating tween.

## 11. Development and production

Development, with demo mode as the default way to work:

```bash
uv run scout serve --demo
```
```bash
npm --prefix web run dev
```

```ts
// vite.config.ts. The object form matters: the string shorthand rewrites Host, and same_origin refuses every POST.
server: { port: 5173, proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: false } } }
```

Backend changes need a manual restart. Production:

```bash
npm --prefix web ci
```
```bash
npm --prefix web run build
```
```bash
uv run scout serve
```

## 12. Verification

- **Vitest, pure logic (`web/src/test/`):** the Demo Run feed reaches the expected end state; a feed applied in one batch equals one by one; `onopen` resets but keeps `texts`; `fromLog` places the cursor per status and infers `search` and `postings`; the label table covers every `/meta` node and yields the five back-edges; progress never decreases; tool pairing is first-in-first-out.
- **`tests/test_web_api.py`, demo graph with `demo_delay=0`,** through `TestClient(app, base_url="http://127.0.0.1")`. The base URL is required, since the Host guard refuses the default `testserver`. It can read SSE to a Pause because the stream is bounded. Covers every endpoint and refusal shape, `caught_up` before any token, 204, `live_from`, cancel then resume, downloads, both guards, an http-only `url`, the catch-all.
- **Contract:** a pytest runs a Demo Run and compares its events and `/meta` with the committed `web/src/test/demo-run.json`, which Vitest feeds to the reducer. Types in `api/types.ts` are hand-written, and this keeps them honest. SSE events aren't in OpenAPI anyway.
- **`scripts/smoke_web.py`, not in CI:** a browser path through a Demo Run: start, each Pause including a refused edit, reload mid-Run, stop and resume, Done, Brief. Uses `chromium.launch(channel="msedge")`, so no browser download or repo dependency.

```bash
uv run --with playwright python scripts/smoke_web.py
```

- **Live:** one real Run by hand, since the demo proves the plumbing and not how real notes read.
- **Skip-list:** no pixel tests, component-render tests or animation assertions.

## 13. Build checklist

Each pass leaves its check behind. No test calls an LLM or a jobs API.

**Pass 1: API and demo.**
1. Add the dependencies and `.gitignore` entries. Make the §3 Controller changes and `graph_topology()`. Test: `attached` returns the live handle and then none; `log_start` matches after a resume.
2. `runtime/demo.py`. Test: a Demo Run emits every event type, through all three Pauses to `done`, and "fail" stops once and resumes.
3. `clients/web.py` and `scout serve`. Test: `tests/test_web_api.py`.

**Pass 2: skeleton.** `web/` scaffold, `api/`, router, shell, sidebar with polling, composer, and production static serving. Check: start a Demo Run and see it in the sidebar. Test: the catch-all serves `index.html`.

**Pass 3: stream.** `steps.ts`, `reducer.ts`, `fromLog.ts`, `useRun.ts`, turn and tool blocks, endings, Stop, reconnect, auto-scroll. Test: the Vitest suite and the contract file.

**Pass 4: Pauses.** Three cards, `PlanEditor`, refusal handling. Check by hand through a Demo Run, including a refused edit and a second tab.

**Pass 5: trace.** The SVG panel, progress bar and narrow strip, as static state with no tweens yet. Test: back-edges and progress.

**Pass 6: Brief.** All §9 components, `Evidence`, downloads, the aborted view, the print stylesheet. Check by hand with `demo_brief`, then with one real Brief from `runs/`.

**Pass 7: motion.** `motion.ts` and the §10 table. Check under OS reduced motion, and that a reload plays no one-shots.

**Pass 8: finish.**
1. `scripts/smoke_web.py`.
2. One live Run by hand.
3. Delete `clients/streamlit_app.py`, `clients/streamlit_bridge.py` and the `streamlit` group, then `uv lock`. Correct `event_line`'s docstring in `cli.py` and "shared by every client" in `pauses.py`.

**If time runs short,** cut in this order, since each is additive and the UI stays correct without it: motion's one-shots, then the narrow layout, then print, then the trace's loop dot. Keep streaming, Pauses, the Brief and Evidence, which carry a Run from start to finish.

## 14. Excluded and deferred

Deliberate deferrals are in [future-scope.md](future-scope.md): dark mode, per-tool-call IDs, a global event feed, auth, and Run management. The Infra shell's API would wrap the Controller separately, and this API is not its design.
