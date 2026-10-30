# Component breakdown and build order

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 12, 13, 14, 15

## Question

Into which components does the system split (each to become its own LLD/build effort), what does each own (responsibility, boundary, the slice of state it reads and writes, its seams to neighbours), and in what order are they built under [What is the build priority order?](02-build-priority-order.md)?

Inputs: the graph in [What is the node-level graph shape?](06-graph-shape.md), the decisions in tickets 01–11, and the research findings from tickets 12–15. The breakdown should also place the infra shell (API, queues, workers, concurrency, MiniStack) as a future-phase component with its seam to the Run Controller.

## Answer

Resolved by grilling. Components are cut by **concern** (one per graph stage plus supporting parts), not per node or per tier. Each becomes its own LLD/build effort.

| # | Component | Owns | State slice it writes |
|---|---|---|---|
| A | **Kernel** | state schema + reducers, domain types, LLM tier factory (OpenRouter, fallbacks, validation retry), Jev classifier wrapper + thresholds | `run_log` reducer (append-only, every node writes) |
| B | **Jobs Data Gateway** | Adzuna + USAJOBS clients, L1 cache, budget guard, replay mode, expiry + sweep; L2 store as a later pass | none (outside the graph) |
| C | **Request & Plan** | `intake`, `clarity_check`, `clarify` (Pause), `plan`, `plan_review` (Pause) | Hiring Request, Clarifying Questions + answers, Assumptions, Search Plan |
| D | **Collection** | `@tool`s, `fetch_agent`, `tools` executor, `collect`, `relevance`, Sufficiency rule, `broaden`, `low_data_review` (Pause) | tool messages, Postings, Sample, attempt count |
| E | **Analysis** | `batch_extract` + Send fan-out + reducer, `stats` | per-Posting extractions, stats |
| F | **Brief** | `write_brief`, `critic`, `render`, Run Notes assembly from `run_log` | brief draft, critic verdicts, final JSON + Markdown |
| G | **Runtime** | StateGraph wiring and compile, SQLite checkpointer + Store, run registry, Run Controller, event stream, Pause protocol, concurrent-resume guard | nothing in graph state; owns threads + registry |
| H | **Clients** | CLI (Pause UX, `--resume`, `--focus`, progress); Streamlit later | none (Run Controller only) |
| I | **Long-term memory** | preferences namespace in the Store, read by `intake` | preferences |
| J | **Infra shell** (future phase) | API, queue, workers on MiniStack; wraps the Run Controller, never the graph | none |

**Boundary rules**
- Each stage owns its slice of state; slices are *declared* in the Kernel, and no component writes another's slice. This is the state ownership map.
- Pause nodes live with the stage whose decision they gate; Runtime owns the Pause *protocol* (payload shape, re-show on return, `Command(resume=…)`, `durability="sync"`).
- Graph wiring lives in Runtime; stage components export only nodes and router functions.
- Critic, streaming and Run Notes are passes over existing components (Brief, Runtime + Clients, Brief), not new boundaries.
- `samples/`, README and write-up are a final delivery task, not a component.

**Build order: tier passes across components**, under [What is the build priority order?](02-build-priority-order.md). Each component's LLD covers all its tiers; building happens in passes.
1. **Must-have walking skeleton**, in order: Kernel → Gateway (L1, budget, replay, Adzuna) → Runtime + CLI (SQLite and Pause protocol from day one, since durable resume is non-negotiable) → Request & Plan (clarify only) → Collection → Analysis (sequential extract) → Brief (no critic).
2. **Recommended**: `plan_review`, `low_data_review`, Send fan-out, fallbacks, `--focus`, USAJOBS, Streamlit.
3. Streaming → 4. Infra shell (J) → 5. Critic (F) → 6. Long-term memory (I). Gateway L2 lands in pass 2 or later.

**Fog reassigned to component LLDs** (LLD-level, so beyond this map): currency/period normalisation, multi-source stats, batching → Analysis; Confidence Tag + Hiring Outlook rules → Brief; Adzuna aggregate endpoints → Gateway; `--focus` effects → Request & Plan + Clients; streaming event model → Runtime; memory contents → Long-term memory; infra internals and shared daily budget → Infra shell; sample-run strategy → delivery task.
