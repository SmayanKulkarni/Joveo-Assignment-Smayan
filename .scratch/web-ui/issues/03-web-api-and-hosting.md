# Web API and hosting

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [Research: delivering Run events over FastAPI SSE](01-research-sse-over-fastapi.md)

## Question

What is the HTTP surface that lets a browser do everything the CLI does, and what does it need from the Run Controller?

- Endpoints and shapes: start a Run (request text, focus), list Runs, read one Run (`RunView`), resume with an answer, cancel, the event stream, the graph topology, and the Brief files. Status codes for `UnknownRun`, `RunLocked`, `NotResumable`, `InvalidAnswer` and `BalanceTooLow`.
- The wire format of an event, given [Research: delivering Run events over FastAPI SSE](01-research-sse-over-fastapi.md). `RunEvent` is already a discriminated union on `type`; say whether it goes out unchanged.
- How a browser re-attaches to a Run that is still live after a reload or in a second tab. The Controller has no method for this today, and [future scope](../../docs/lld/future-scope.md) says re-attach is "built on its own API": decide the smallest Controller change, or why none is needed.
- How a client builds a Pause form: whether the API exposes each answer model's JSON Schema from `ANSWERS`, or the UI hard-codes the three kinds.
- Hosting: how `scout serve` opens one Controller in the app lifespan, serves the built `web/` files, and runs in the no-LLM demo mode on `fake_deps` and the stub graph.
- How the server handles shutdown with a Run live (the Run ends `failed` and resumable, as a CLI exit does).

Resolution is the endpoint table, the Controller change if any, and the demo-mode switch.

## Answer

Decided by the agent (the user delegated every decision on 2026-10-31), then checked with a throwaway spike on the real `RunController` over a paced demo graph: real HTTP, the browser pane's `EventSource`, Starlette's `TestClient`, and the Vite proxy. FastAPI 0.162.0, uvicorn 0.54.0, Vite 8.3.5. The spike is outside the repo (session scratchpad, `web-spike\`). "Verified" below means it was run there.

**Endpoints, all under `/api`, all `async def`.** A sync path op would run on a thread pool, but the lock connection and `aiosqlite` belong to the loop thread.

| Method, path | Body | Success | Refusals |
|---|---|---|---|
| `GET /meta` | | `{graph, dimensions, countries, categories, confidence_key, demo}` | |
| `GET /runs` | | `list[RunRecord]`, newest first | |
| `POST /runs` | `{request_text, focus}` | 201 `{thread_id}` | 402, 502, 422 |
| `GET /runs/{id}` | | `RunDetail` | 404 |
| `POST /runs/{id}/resume` | `{answer: dict or null}` | 200 `{thread_id}` | 404, 409, 422, 402, 502 |
| `POST /runs/{id}/cancel` | | 200 `Stopped` | 404, 409 `not_live` |
| `GET /runs/{id}/events` | | 200 SSE, or 204 when nothing is live here | 404 |
| `GET /runs/{id}/brief.json`, `brief.md` | | the file, as a download | 404 |

Refusals share one body, `{code, message, errors?}`: `unknown_run` 404, `run_locked` 409, `not_resumable` 409, `not_live` 409, `no_brief` 404, `invalid_answer` 422, `invalid_request` 422 (FastAPI's own validation errors, reshaped by one handler), `balance_too_low` 402, `upstream` 502 (`httpx.HTTPError` from `check_balance`).

**`InvalidAnswer` must be cleaned.** Pydantic's raw `errors()` hold exception objects in `ctx`, which JSON can't carry. The handler sends only `{loc, msg}` and strips the "Value error, " prefix. **Verified** shapes: a field error has `loc: ["plan", "radius_km"]`, a model-level error (reject with no feedback) has `loc: []`, and a refused answer leaves the Run `paused`.

**`RunDetail`, not `RunView`.** `RunView.state` holds LangChain messages and every Posting's full text, so the API returns a slim model built from it: `record`, `request_text`, `focus`, `pause`, `stopped_at`, `run_log` (`node`, `kind`, `message` only), `live_from`, `brief`, and `sample` (`key`, `title`, `company`, `location`, `url`, `posted_at`, only when there is a Brief). `url` is null unless the scheme is http or https, the same guard as `brief/markdown.py`'s `_link`, so the client never receives a `javascript:` link.

**Wire format.** `RunEvent` goes out unchanged, as `model_dump_json()` in one unnamed message, plus one synthetic message that is not a `RunEvent`: `{"type": "caught_up"}`, sent once the buffered replay has been written. The client needs that boundary to apply a replay with no animation and to know where lost tokens could be. **Verified exact:** on attaching mid-Run, 0 `Token` or `Reasoning` events came before `caught_up`, because they are queue-only and the queue is read after the replay. `Done.paths` is sent unchanged and the UI ignores it.

**Controller changes, the only ones.**
1. `_live` becomes `dict[str, RunHandle]`, with `attached(thread_id) -> RunHandle | None`. This is re-attach. The handle already supports several subscribers, so nothing else is needed.
2. `RunHandle.log_start`, the `log_len` already passed to `_spawn`. `RunDetail.live_from` reports it, or null with no handle.
3. `RunHandle.buffered`, the buffer's length, read with no await before `events()` takes its snapshot.
4. `_brief_paths` becomes public as `brief_paths`.
5. The demo switch below.

**A refinement to [Trace graph](05-trace-graph.md): rebuild from `run_log`, not State fields.** A resumed Run gets a new handle with a fresh buffer, so a replay covers only the events since the last resume. The client's starting view for a reload is therefore built from `run_log[:live_from]`, and the replay supplies everything after it. That has no overlap and no race, because `live_from` is fixed per handle, and it replaces the State-field rule, so `RunDetail` needs no route facts. Three nodes write no log line in normal use (`fetch_agent`, `tools`, `batch_extract`), so the rebuild infers them: a `collect` line means Search ran before it, and a `normalise_skills` line means Read postings ran before it.

**Stream lifecycle, verified in the browser pane.** A live handle gives SSE. With no handle, a dependency raises `HTTPException(204)` and `EventSource` goes to `readyState` 2 (closed) with no retry in 7 s. An unknown ID gives 404, which also stops it. `Paused` reaches the client just before the task ends, so right after it `GET /runs/{id}` still said `running` with a live handle. **The client trusts the event and never refetches to confirm it.** The sidebar's refetch after a terminal event waits 300 ms, and `Done`'s fetch of the Brief retries while the status still says `running`. An immediate resume right after `Paused` returned 200 in the check, but the client retries once at 300 ms on `run_locked`, which also covers reconcile's probe (Runtime LLD §8).

**Cancel** is `handle.cancel()` on the attached handle. **Verified:** it gives `Stopped(node, "cancelled")` and `failed`, and Resume with `answer: null` goes on from that node. On a paused Run it is 409 `not_live`, since abort is the Pause's own answer.

**Pause forms:** the API does not expose JSON Schema. The UI renders three typed kinds, because a generated form could not read well, and `/meta` serves only the lists it can't hard-code without drift (countries, categories, dimensions, the Confidence key).

**A Run started by the CLI** shows `running` with `live_from: null`. The UI says it is running elsewhere and polls `GET /runs/{id}`.

**Local security, which the delegation did not remove.** The server has no auth, can spend OpenRouter and Adzuna quota, and any web page can send requests to localhost.
- Binds `127.0.0.1` only, with no `--host` flag.
- `TrustedHostMiddleware(allowed_hosts=["127.0.0.1", "localhost"])` stops DNS rebinding. **Verified:** a foreign `Host` gets 400.
- A `same_origin` dependency on every POST: if `Origin` is present and its host differs from `Host`, 403. **Verified**, including a body-less cross-origin cancel, which JSON content-type checks alone would miss. A `text/plain` JSON POST is also refused by FastAPI (422).
- No `BaseHTTPMiddleware`, so nothing sits between the SSE response and disconnect handling. Both guards are pure ASGI or a dependency.
- **Vite's proxy must be `{target, changeOrigin: false}`.** With the string shorthand, **verified**, every dev POST gets 403, because `Host` no longer matches `Origin`. With the object form, same-origin POSTs give 201, a foreign one 403, and SSE and 204 pass through.

**Hosting.** `scout serve [--port 8000] [--demo]` is a new subcommand in `clients/cli.py`, importing `clients/web.py` lazily. `uvicorn.run(app, host="127.0.0.1", port=port, timeout_graceful_shutdown=3)`. The lifespan opens one `RunController` on `app.state`. Static files: `/assets` mounted from `web/dist/assets`, and a catch-all GET returns `index.html` so `/runs/:id` reloads work, with `/api/*` staying a real 404. If `web/dist` is missing, the catch-all says to run the build. Uvicorn runs one worker and no `--reload`, since a reload would stop live Runs.

**Shutdown. Verified:** with a Run live, the lifespan exit cancels it, and after a restart it reads `failed`, `cancelled`, with no live handle, and it is resumable. The existing `open()` already does this.

**Concurrent Runs. Verified** with two at once on one Controller. There is no Run limit. On the real Gateway they share the atomic daily budget counter, so the first come is served first, which settles the HLD's open question for this slice.

**Demo switch.** `Settings.demo: bool = False`, and `demo_delay: float = 0.4`. `open_deps` yields `fake_deps` marked `demo=True`, `_check_balance` skips, and `build_graph` overlays `demo_nodes()` and `DEMO_ROUTERS` from a new `runtime/demo.py`. The bare stubs emit no tokens, tools or delays, so a UI can't be built against them. **Verified:** a small `BaseChatModel` scripted with `_astream` delivers real `Token` and `Reasoning` events through `messages` mode, and six `Send`s give real `ExtractProgress` 1/6 to 6/6 with one `NodeStarted`. `--demo` builds its settings with `make_settings` so it needs no `.env`, and uses `.cache/demo/` for `runs_db` and `runs_dir`, so demo Runs never reach real history. A request containing "fail" raises once in `normalise_skills`, which exercises `Stopped` and Resume.

**Tests.** `TestClient(app, base_url="http://127.0.0.1")` works and reads SSE to a Pause, since the stream is bounded (**verified**). Its default host is refused by the Host guard, which is why the base URL is set.

**Noticed:** each load logs "Blocked deserialization" for `HiringRequest`, `LogKind`, `RunLogEntry`, `ClarifyingQuestion`, `SearchPlan` and `MarketStats`. `State.model_validate` copes, so it is noise, but a long-lived server would show it in its log. Pass 1 lists them in `ALLOWED_MSGPACK`.

**Not verified:** a real tab close, or a real reverse proxy. Neither changes the design for one local process.
