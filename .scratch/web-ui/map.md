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

## Not yet specified

- **Persisted event history.** Future scope defers it. If a finished Run's trace and tool lines must survive a reload, the Controller needs to store events; [Trace graph](issues/05-trace-graph.md) decides whether `run_log` and state are enough. Revisit once that ticket closes.
- **Responsive depth.** How far the layout bends below tablet width. Revisit after the shell prototype.
- **Dark mode and theming.** Revisit after the shell prototype, and only if it costs little.

## Out of scope

- Infra shell internals: API gateway, queue, workers, auth, multi-user, deployment and hosting.
- Deleting, renaming or searching Runs: the Controller has no such methods, and a sidebar of read-only history is the destination.
- The Long-term memory (preferences) UI: it belongs to that LLD.
- What each Pause asks, what each `focus` value changes, node bodies: stage LLDs.
- Writing the web UI code: separate build effort after this map.
