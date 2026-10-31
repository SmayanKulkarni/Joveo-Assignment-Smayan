# Research: delivering Run events over FastAPI SSE

Type: research
Status: open
Assignee: smayankulkarni05
Blocked by: none

## Question

Which streaming transport should the web API use to push `RunEvent`s to the browser, and what are its limits on the pinned stack and Windows?

- Server-Sent Events from a FastAPI/Starlette `StreamingResponse` over an async generator that wraps `RunHandle.events()`: how the generator learns the client disconnected (so a closed tab drops its subscriber and never cancels the Run), how a keep-alive comment behaves, and what stops proxy or dev-server buffering.
- Browser `EventSource` against a `fetch` stream reader: reconnect behaviour, `Last-Event-ID`, GET-only, the per-origin connection cap on HTTP/1.1, and how Vite's dev proxy treats each.
- Whether several subscribers on one `RunHandle` (two tabs) work, given the Controller's snapshot-then-queue design.
- Whether `uvicorn` on Windows needs any flag for clean shutdown while a stream is open.

Use the library docs and a throwaway script against the pinned versions; capture findings in the ticket.
