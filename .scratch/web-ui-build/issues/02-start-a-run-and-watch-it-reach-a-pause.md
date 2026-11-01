# 02: Start a Run and watch it reach a Pause

**What to build:** the tracer bullet, through every layer. A user runs `scout serve --demo`, opens the app, types a Hiring Request, picks focus chips, presses Start, lands on `/runs/:id`, and watches Step lines appear live until the Run stops at its first Pause. Spec: [Web UI LLD](../../../docs/lld/web-ui.md) §2, §4 (start, read, events, meta, security, hosting), §5 (frame, routes, composer), §7 (the stream's start only), §11, §13 pass 1 step 3 and pass 2.

**Blocked by:** 01: Controller seams and the Demo Run

**Status:** done

Scope limits, each lifted by a later ticket:
- The stream is one line per turn: Step label and notes. No tokens, tool cards or collapse (07).
- A Pause shows only "Waiting for you", with no form (03).
- No sidebar (06), trace panel (10) or animation (11). The layout leaves room for them.
- Opening a Run from a URL shows its request and status only. Rebuilding its history is 08.

- [x] `GET /api/meta`, `GET /api/runs`, `POST /api/runs`, `GET /api/runs/{id}` and `GET /api/runs/{id}/events` work as the LLD's table says, and all path ops are `async def`
- [x] Refusals use the one `{code, message, errors?}` body, including reshaped FastAPI validation errors
- [x] `RunDetail` is returned rather than `RunView`, with a `url` of null unless http or https
- [x] The stream sends each event unchanged, one `caught_up` after the replay, and 204 when nothing is live; an unknown ID gets 404
- [x] The client closes its `EventSource` on `Paused`, `Done` and `Stopped`, and resets to its base on `onopen`
- [x] The label table covers every `/meta` node and yields exactly the five back-edges, checked by a Vitest test, so a new node can't go unlabelled
- [x] A foreign `Host` gets 400; a POST with a foreign `Origin` gets 403, with and without a body
- [x] `same_origin` passes through the Vite dev proxy, which uses `changeOrigin: false`
- [x] The server binds loopback only and shuts down with an open stream inside `timeout_graceful_shutdown`
- [x] The production build is served by FastAPI; `/runs/:id` survives a reload; `/api/*` stays a real 404; a missing `web/dist` says to run the build
- [x] The composer refuses a blank request, Enter submits, Shift-Enter adds a line
- [x] An unknown Run ID shows "Run not found" with a link to `/`
- [x] API behaviour above is covered in `pytest` through `TestClient` with the loopback base URL
- [x] Checked by hand in the browser through a Demo Run to the first Pause
