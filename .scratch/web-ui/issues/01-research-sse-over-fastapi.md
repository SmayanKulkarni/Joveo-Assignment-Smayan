# Research: delivering Run events over FastAPI SSE

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

Which streaming transport should the web API use to push `RunEvent`s to the browser, and what are its limits on the pinned stack and Windows?

- Server-Sent Events from a FastAPI/Starlette `StreamingResponse` over an async generator that wraps `RunHandle.events()`: how the generator learns the client disconnected (so a closed tab drops its subscriber and never cancels the Run), how a keep-alive comment behaves, and what stops proxy or dev-server buffering.
- Browser `EventSource` against a `fetch` stream reader: reconnect behaviour, `Last-Event-ID`, GET-only, the per-origin connection cap on HTTP/1.1, and how Vite's dev proxy treats each.
- Whether several subscribers on one `RunHandle` (two tabs) work, given the Controller's snapshot-then-queue design.
- Whether `uvicorn` on Windows needs any flag for clean shutdown while a stream is open.

Use the library docs and a throwaway script against the pinned versions; capture findings in the ticket.

## Answer

Researched 2026-10-31. The repo has no web deps yet, so "pinned" means a fresh venv: FastAPI 0.162.0, Starlette 1.10.0, uvicorn 0.54.0 (h11), Windows 11, Python 3.12, Vite 8.3.5, and the Claude desktop browser pane (Chromium 152). Test scripts are outside the repo, in the session scratchpad `sse-research\`. They use a stand-in with the same `events()` shape as `RunHandle`, not the real Controller.

### Recommendation

- **Transport: `EventSource` on `GET /runs/{id}/events`.** Starting a Run and answering a Pause are separate POSTs, so GET-only costs nothing, and there is no auth header to set. Reconnect and parsing come free. A fetch reader only buys headers and POST.
- **Server: FastAPI's built-in `EventSourceResponse`**: an `async def` path op that `yield`s `ServerSentEvent`s from `handle.events()`. It sets `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`, and sends `: ping` after 15 s idle. Needs FastAPI >= 0.135.
- **Framing: one default (unnamed) message per `RunEvent`; `data` is the event JSON with its `type` discriminator.** The client has one `onmessage` and switches on `type`. No `event:` name and no `id:`, since Controller events carry no sequence number.
- **Disconnect needs no code in the generator.** The `finally` in `RunHandle.events()` already unregisters the queue, and the Run task is never touched. Never wrap `events()` in `asyncio.wait_for` to make pings: a timeout kills the generator.
- **The client must `close()` on any terminal event** (`Paused`, `Done`, `Stopped`). When the server ends a stream normally the browser reconnects, `events()` replays the whole buffer and ends again, forever (every ~3 s in Chrome). On every `onopen` the client also resets its view, because a reconnect replays from the start.
- **The sidebar must not hold its own stream.** Over HTTP/1.1 the cap is 6 connections per origin, across tabs. The sidebar polls or refetches `GET /runs` on terminal events; only the open Run page streams.
- **Windows: start uvicorn with `timeout_graceful_shutdown` (3 is enough).** Without it, a shutdown with an open stream hangs. No other flag.

### Findings

**Disconnect**
- Under uvicorn the ASGI `spec_version` is `"2.3"` (`uvicorn/protocols/http/h11_impl.py` L210, `httptools_impl.py` L228), so Starlette's `StreamingResponse.__call__` runs `listen_for_disconnect` beside `stream_response` in a task group and cancels the other when either ends (`starlette/responses.py` L262-285, [Starlette](https://github.com/encode/starlette)). An idle consumer is cancelled, not noticed on the next write. A server advertising >= 2.4 takes the other branch, where only a failed `send` signals disconnect, so keep-alive pings are what would detect a dead tab there.
- FastAPI iterates the generator in a producer task on the request's exit stack, so cancellation arrives as `CancelledError` in the generator's `await queue.get()` (`fastapi/routing.py` L598-658, [FastAPI](https://github.com/fastapi/fastapi)).
- **Verified:** with the producer silent for 60 s, the idle generator got `CancelledError` and ran `finally` the moment the client closed, for a hand-written `StreamingResponse` and for `EventSourceResponse`. Subscribers went 1 to 0 and the producer (the Run stand-in) kept going. Same on a TCP RST (`SO_LINGER 0`) and on a `fetch` abort through the Vite proxy.

**Keep-alive**
- The spec suggests a comment line "every 15 seconds or so" because legacy proxies drop quiet connections ([WHATWG](https://html.spec.whatwg.org/multipage/server-sent-events.html)). FastAPI's default is 15 s ([tutorial](https://fastapi.tiangolo.com/tutorial/server-sent-events/), `fastapi/sse.py`).
- **Verified:** `: ping\n\n` (8 bytes) arrived at 15.6, 30.7 and 45.7 s on an idle stream. `EventSource` fires nothing for comments (spec; no `onmessage` fired in the Chrome runs).
- **Verified pitfall:** `asyncio.wait_for(agen.__anext__(), t)` on timeout runs the generator's `finally`, and the next `__anext__` raises `StopAsyncIteration`. FastAPI avoids it with a separate producer task and says so in its source comments (L598-612).

**Buffering**
- The browser fails the connection unless the status is 200 and the type is `text/event-stream` (spec, [fetch step](https://html.spec.whatwg.org/multipage/server-sent-events.html)). `Cache-Control` and `X-Accel-Buffering` were present in the response headers; the latter only matters behind nginx.
- Starlette's `GZipMiddleware` excludes `text/event-stream` (`starlette/middleware/gzip.py` L26). **Verified:** with `GZipMiddleware(minimum_size=1)` and `Accept-Encoding: gzip`, events still arrived un-encoded and one by one. A custom compression middleware would need the same exclusion.
- **Verified:** the Vite dev proxy (`http-proxy-3` in Vite 8.3.5, [Vite docs](https://vite.dev/config/server-options)) forwards `fetch` streams unbuffered (events at 183, 402, 606 ms; headers intact; no `content-encoding`) and propagates an abort to the generator. Vite's docs say nothing about streaming, so this rests on the test. `EventSource` through the same proxy also streamed and reconnected in Chrome.

**EventSource vs fetch reader**
- `new EventSource(url, {withCredentials})` is the whole constructor: GET only, no custom headers or body ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/EventSource/EventSource)). A token would have to ride in the URL or a cookie. A fetch reader (`response.body.getReader()` + `TextDecoder`, [MDN](https://developer.mozilla.org/en-US/docs/Web/API/Response/body)) allows both, but then you write the parser, reconnect and abort yourself.
- Reconnect: after any closed connection, with an implementation-defined delay ("a few seconds"); `retry:` changes it, `close()` ends it, and a non-200 (204 is the documented stop signal) fails without retry (spec). **Verified in Chrome:** after a normal stream end it reconnected every ~3.0 s, replaying everything each time (`error` with `readyState 0`, then `open`).
- `Last-Event-ID` goes out on reconnect only when an `id:` was seen. **Verified:** the server saw `Last-Event-ID: 4`. It is unusable here: events have no ID, `Token` and `Reasoning` are live-only, and the buffer is a `maxlen` deque, so resuming would need a new counter. Decision: omit ids and rebuild on `onopen`.
- Connection cap: about 6 per browser and origin on HTTP/1, shared across tabs; HTTP/2 negotiates streams, default 100 ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)). **Verified in Chrome over `http://localhost` (`nextHopProtocol: http/1.1`):** of 8 `EventSource`s to one origin, 6 opened and 2 stayed `CONNECTING`; a plain `fetch` and a page navigation to that origin also queued behind them. A sidebar stream plus one stream per open Run tab would exhaust it fast. Browsers do not speak cleartext HTTP/2, and uvicorn 0.54 offers HTTP/2 only through the optional `zttp` protocol (`uvicorn/config.py` L38, L442), so localhost stays HTTP/1.1.

**Two subscribers**
- **Verified:** one producer (15 events, 0.3 s apart), subscriber A from the start, subscriber B joining 2 s in. Both received ids 0-14 in order, with no gaps or duplicates, for both response styles, and subscribers fell to 0 after. This matches the snapshot-then-register-without-await design. A finished Run's `events()` replays and returns, so a reload works as a short stream.

**Windows shutdown**
- Uvicorn handles SIGINT, SIGTERM and, on Windows, SIGBREAK (`uvicorn/server.py` L45-50). `shutdown()` waits on open connections with no bound unless `timeout_graceful_shutdown` is set (`server.py` L280-330).
- **Verified:** with one open stream, `CTRL_BREAK_EVENT` logged "Waiting for connections to close" and the server was still running after 40 s (both response styles). With `--timeout-graceful-shutdown=3` it logged "Cancel 1 running task(s)", ran lifespan shutdown, and exited in 3.2 s. With no stream open it exited in 0.2 s. `Process.terminate()` exits at once. The exit code 3 is what Ctrl-Break gives on Windows, with or without a stream.
- Lifespan shutdown (where `RunController.open` closes the store) runs only after that wait, so the timeout also bounds when the SQLite checkpointer closes.

### Not verified

- A real tab close in Chrome. I navigated the page away, which closed all 6 held streams and ran each server `finally`. A tab close, crash or sleep was not driven.
- Any real reverse proxy (nginx, corporate proxy). `X-Accel-Buffering` was checked only as a header.
- `CTRL_C_EVENT` itself (a child in its own process group cannot receive it from a script); Ctrl-Break goes through the same uvicorn handler.
- `uvicorn[standard]` (httptools, uvloop) and `--reload`; I used h11. Source shows both protocol classes report `spec_version` 2.3.
- Firefox and Safari reconnect timing and connection caps.
- The real `RunHandle`: a 5000-event replay through one connection, high-rate `Token` chunks, and `model_dump_json` of the real `RunEvent` models through `ServerSentEvent`.
