# Web API and hosting

Type: grilling
Status: open
Assignee: none
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
