# Web UI

Label: wayfinder:map
Parent: [Talent Market Scout: HLD](../talent-scout-hld/map.md) (the web UI that [docs/HLD.md](../../docs/HLD.md) §8 and [future scope](../../docs/lld/future-scope.md) leave to the Infra shell, pulled forward as a thin slice)

## Destination

`docs/lld/web-ui.md`: an LLD of a browser UI for the whole system, precise enough to build straight from. A user starts a Run, watches it live (streamed tokens, tool-call loading states, a trace graph with animated progress), answers Pauses, reads the Market Brief, and finds every earlier Run in a chat-style sidebar. Nothing is left to decide. Building it is a separate effort after this map.

## Notes

- Domain: a new client over the Run Controller, plus the thin web API it needs. Vocabulary: `GLOSSARY.md`. Spec: `Joveo_Talent_Market_Agent- Assessment.pdf`. Deadline Mon 2 Nov 2026, 9:00 AM, so this map stays lean and every ticket picks the simplest thing that reads well.
- Fixed upstream: [docs/lld/runtime.md](../../docs/lld/runtime.md) (Run Controller §6, events §10, CLI and Streamlit §12–13), [docs/lld/future-scope.md](../../docs/lld/future-scope.md) (Runtime and Clients rows), [Clients flow](../runtime-lld/issues/03-clients-flow.md), [Research: live streaming sources](../runtime-lld/issues/05-research-live-streaming-sources.md).
- Skills: `grilling` + `domain-modeling` for grilling tickets, `prototype` for prototype tickets, `research` for research tickets. Nothing here touches LangChain, so `langchain-router` applies only if a ticket reaches into stage or Controller code.
- Standing preferences: inherited from the Runtime map (Pydantic v2, `uv`, Python 3.12, `src/talent_scout/`, `pytest`). Code comments are short and say why, never headers.
- On 2026-10-31 the user told the agent to make every decision itself and chart the map. So the scope below is decided at charting, and each ticket will be decided by the agent and say so, as the Runtime map did.
- Decided at charting:
  - **Stack.** A FastAPI app hosting one `RunController` for the process lifetime, started as `scout serve`, and a Vite + React + TypeScript single-page app in `web/`. GSAP (with `@gsap/react`) does all animation; the user named it. The built app is served as static files by FastAPI, so there is one process and one port.
  - **No Infra shell.** No queue, workers, auth or multi-user. The Controller still lives in the server process, so a browser can close and reopen without stopping a Run, but a server restart behaves as a CLI exit does: the Run is `failed` and resumable.
  - **The API only adapts the Controller.** It adds no Run logic. Controller changes are allowed only where [Web API and hosting](issues/03-web-api-and-hosting.md) shows one is needed, such as re-attaching to a live Run.
  - **Graph topology comes from the backend.** `runtime/graph.py`'s `EDGES`, `CONDITIONAL` and `OWNERS` are the one source, and the UI draws from them rather than copying the graph.
  - **Friendly node labels return.** [future-scope](../../docs/lld/future-scope.md) deferred them "until showing the live view to clients"; this is that. The label table is decided in [Trace graph](issues/05-trace-graph.md).
  - **Streamlit is deleted** when the web UI lands, as future scope says.
  - **No-LLM demo mode.** The server can run on `fake_deps` and the stub graph, so the UI is built and checked without OpenRouter or a jobs API.

## Decisions so far

<!-- one line per closed ticket -->

- [Research: delivering Run events over FastAPI SSE](issues/01-research-sse-over-fastapi.md): use `EventSource` on a GET stream with FastAPI's `EventSourceResponse`, one unnamed message per `RunEvent` and no event IDs; disconnect needs no code but the client must `close()` on `Paused`, `Done` and `Stopped`; the sidebar must not hold its own stream (6 connections per origin); uvicorn needs `timeout_graceful_shutdown` on Windows.
- [Research: graph rendering and GSAP in React](issues/02-research-graph-rendering-and-gsap.md): hand-written SVG on a fixed column grid built from the backend topology, with no React Flow or layout library; `gsap` 3.15.0 and `@gsap/react` 2.1.2 on React 19, all plugins free, one scoped `useGSAP` with `gsap.matchMedia` for reduced motion; about 97 kB gzip against 156 kB for React Flow.
- [Trace graph](issues/05-trace-graph.md): 14 user-level steps in four bands, merged from the 17 raw nodes by a UI label table over a backend-served topology; a vertical rail with only back-edges drawn, a counter badge and travelling dot on loops, one bar for extraction, a weighted never-decreasing progress bar, and a reopened Run rebuilt from `get_run` state, so no event history is stored.
- [App shell and history sidebar](issues/04-app-shell-and-history-sidebar.md): a fixed sidebar with a pinned "Needs you" group above Today, Yesterday and earlier groups, a centred Run column, a right trace panel (a strip and slide-over below about 900 px), routes `/` and `/runs/:id`, and the sidebar polling the Run list; the prototype is linked there.
- [Web API and hosting](issues/03-web-api-and-hosting.md): nine `/api` endpoints that only adapt the Controller, with five small Controller changes (re-attach through `attached`, `log_start`, `buffered`); a synthetic `caught_up` message and 204 when nothing is live; a slim `RunDetail`, rebuilding reloads from `run_log[:live_from]`; loopback plus Host and Origin guards; `scout serve --demo` on a paced demo graph. Checked on the real Controller.
- [Live Run view](issues/06-live-run-view.md): a turn is one visit to one Step, with typed blocks from one pure reducer batched per frame; `onopen` resets to a `base` state while live text survives; the client trusts terminal events because the status row lags them.
- [Pause forms](issues/07-pause-forms.md): three typed cards posting exact payloads, a structured form for plan edits rather than JSON, two-step abort, and field-level `InvalidAnswer` errors; `pauses.py` stays for the CLI.
- [Brief view](issues/08-brief-view.md): rendered from structured data in `brief.md`'s section order, with inline Evidence (cited Stats and linked Postings), never colour alone, Run Notes open with Caveats first, and print as a stylesheet only.
- [Motion with GSAP](issues/09-motion-with-gsap.md): React renders the final state and GSAP only plays the way in, through one `useMotion` helper; an animation table with shared tokens, and no per-token tween.
- [Frontend build and verification](issues/10-frontend-build-and-verification.md): npm with exact pins, no router, store or CSS library; FastAPI in the main dependencies; Vitest, API tests, a contract file and one browser smoke; Streamlit goes last; dark mode deferred.
- [Write docs/lld/web-ui.md](issues/11-write-web-ui-lld-doc.md): the LLD and its 8-pass checklist are written, and the Runtime, HLD, future-scope and glossary docs agree with it. The map is complete.

## Not yet specified

Nothing: the fog is clear. Dark mode was deferred in [Frontend build and verification](issues/10-frontend-build-and-verification.md).

## Out of scope

- Infra shell internals: API gateway, queue, workers, auth, multi-user, deployment and hosting.
- Deleting, renaming or searching Runs: the Controller has no such methods, and a sidebar of read-only history is the destination.
- The Long-term memory (preferences) UI: it belongs to that LLD.
- What each Pause asks, what each `focus` value changes, node bodies: stage LLDs.
- Writing the web UI code: separate build effort after this map.
