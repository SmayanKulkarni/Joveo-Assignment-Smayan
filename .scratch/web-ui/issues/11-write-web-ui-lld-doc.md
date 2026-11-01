# Write docs/lld/web-ui.md

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by: [App shell and history sidebar](04-app-shell-and-history-sidebar.md), [Trace graph](05-trace-graph.md), [Live Run view](06-live-run-view.md), [Pause forms](07-pause-forms.md), [Brief view](08-brief-view.md), [Motion with GSAP](09-motion-with-gsap.md), [Frontend build and verification](10-frontend-build-and-verification.md)

## Question

Does `docs/lld/web-ui.md` say all that was decided, precisely enough to build from, and do the other docs agree with it?

Write the LLD from the closed tickets (the web API, shell, trace graph, live view, Pause forms, Brief view, motion, and build and verification) with a build checklist. Then bring the neighbours in line: [runtime.md](../../../docs/lld/runtime.md) §12–13 (Streamlit replaced, any Controller change), the HLD's client and Infra shell rows, the [future-scope](../../../docs/lld/future-scope.md) Runtime and Clients rows this brings back (web UI, friendly labels, re-attach, Cancel, token display) and any new deferrals, and `GLOSSARY.md` if a new term entered. Resolved when no doc contradicts another and no decision is missing.

## Answer

Done by the agent on 2026-10-31. Wrote [docs/lld/web-ui.md](../../../docs/lld/web-ui.md) from the closed tickets, with an 8-pass build checklist and a cut order. Brought the neighbours in line:
- [runtime.md](../../../docs/lld/runtime.md): §1, §2 and §11 name the web UI; §6 gains `attached`, `log_start`, `buffered` and `brief_paths`; §13 is now a pointer to the new LLD; §14 gains the two demo settings; §17's Infra shell line no longer claims the API.
- [HLD](../../../docs/HLD.md): the client diagrams, the Clients row, the registry note, §10's scope and the build order. It records the web UI as pulled forward, with the Infra shell unchanged.
- [future-scope.md](../../../docs/lld/future-scope.md): removed what this effort brings back (web UI, re-attach, Cancel, token display, friendly labels) and added a Web UI section of new deferrals.
- `GLOSSARY.md`: added Step and Demo Run.

Checked by searching the docs for what each change could contradict. One correction came out of writing it: [Trace graph](05-trace-graph.md) said 13 Steps, but its table and prototype have 14, so the ticket and LLD now say 14.

Runtime §10's "Gateway's `fetch` emits `api_called`" and the build-order history were left alone: they are accurate or historical, and not touched by this effort.

No code was changed, as the map's destination is the LLD. Streamlit still exists until the build's last pass, so runtime.md's pass 2 checklist keeps its history.
