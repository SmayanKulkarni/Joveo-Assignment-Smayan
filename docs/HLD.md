# Talent Market Scout: High-Level Design

The Talent Market Scout turns a **Hiring Request** into an evidence-backed **Market Brief**. A customer success manager can hand the brief to a client. Vocabulary follows [GLOSSARY.md](../GLOSSARY.md). Each decision below is a short summary that links to the ticket holding its full reasoning.

## 1. Scope

This HLD fixes the components, the graph shape, which component owns which part of the state, Pauses and durable resume, where Jev is used, the data gateway, the infra topology and the build order. Each component gets its own LLD/build effort, which decides exact state fields and types, prompt text, retry counts, limits, thresholds, and library and model picks. ([What does the HLD cover?](../.scratch/talent-scout-hld/issues/01-hld-destination-and-lld-deferral.md))

Out of scope: the supervisor multi-agent stretch goal.

## 2. System context

```mermaid
flowchart LR
  user([CSM / user])
  subgraph clients [Clients]
    cli[CLI]
    st[Streamlit · optional]
  end
  rc[Run Controller]
  graph[LangGraph StateGraph]
  db[(SQLite · checkpointer + Store)]
  gw[Jobs Data Gateway]
  adz[Adzuna API]
  usa[USAJOBS API]
  orr[OpenRouter · LLMs + Jev]
  ls[LangSmith]

  user --> cli & st --> rc --> graph
  rc <--> db
  graph <--> db
  graph --> gw --> adz & usa
  graph --> orr
  graph -.traces.-> ls
```

- **Stack**: Python, LangChain + LangGraph, OpenRouter for every LLM call and for Jev, LangSmith tracing. API keys live in the root `.env`.
- **Jobs sources**: Adzuna is the primary source. USAJOBS is used only for US locations and covers federal roles only. The model reaches them through two LangChain tools, `search_adzuna` and `search_usajobs` (the second bound only for US plans), and chooses between them; the Gateway calls the chosen source, and Collection merges the two and collapses Duplicates. The model never calls the APIs directly. ([Gateway query interface](../.scratch/gateway-lld/issues/02-gateway-query-interface.md)) ([Jobs sources and tool execution](../.scratch/talent-scout-hld/issues/03-jobs-sources-and-tool-execution.md))
- **Clients call only the Run Controller.** It offers four operations: start, resume, stream events and get state. Clients never touch the graph directly. ([Client surfaces and the Run Controller](../.scratch/talent-scout-hld/issues/09-client-surfaces-and-run-controller.md))

## 3. Components

The system is split by concern, not one component per node. The Kernel declares each part of the state, and each part has exactly one component that writes it. ([Component breakdown and build order](../.scratch/talent-scout-hld/issues/16-component-breakdown-and-build-order.md))

| # | Component | Responsibility | Part of state it writes |
|---|---|---|---|
| A | **Kernel** | State schema and reducers, domain types, LLM tier factory, Jev classifier wrapper and all Jev thresholds | `run_log` (append-only; every node writes to it) |
| B | **Jobs Data Gateway** | Adzuna and USAJOBS clients, L1 cache, budget guard, replay mode, expiry and sweep; the L2 store comes later | none (outside the graph) |
| C | **Request & Plan** | `intake`, `clarity_check`, `clarify` ⏸, `plan`, `plan_review` ⏸ | Hiring Request, Clarifying Questions and answers, Assumptions, Search Plan |
| D | **Collection** | `search_adzuna` and `search_usajobs` tools, `fetch_agent`, `tools` executor, `collect`, `relevance`, Sufficiency rule, `broaden`, `low_data_review` ⏸ | tool messages, Fetch records, Postings, relevance verdicts, Sample, broadened plans, the low-data answer |
| E | **Analysis** | `batch_extract` (Send fan-out and its reducer), `normalise_skills`, `stats` | per-Posting extractions, skill aliases, stats |
| F | **Brief** | `write_brief`, `critic`, `render`, building the Run Notes from `run_log` | brief draft, critic verdicts, final JSON and Markdown |
| G | **Runtime** | Graph wiring and compile, SQLite checkpointer and Store, run registry, Run Controller, event stream, Pause protocol, concurrent-resume guard | nothing in graph state; owns threads and the registry |
| H | **Clients** | CLI (Pause UX, `scout resume`, `--focus`, progress); Streamlit later | none |
| I | **Long-term memory** | Preferences namespace in the Store, read by `intake` | preferences |
| J | **Infra shell** *(future phase)* | API, queue and workers on MiniStack, wrapping the Run Controller | none |

Boundary rules:
- No component writes another component's part of the state.
- Pause nodes live with the stage whose decision they gate. Runtime owns the Pause *protocol*: the payload shape, re-showing the Pause on return, and resuming.
- Graph wiring lives in Runtime. Stage components export only nodes and router functions.
- Critic, streaming and Run Notes are later passes over existing components, not separate components.

## 4. Graph

Solid lines are fixed edges and dotted lines are conditional edges (each label is the router's outcome). Orange nodes are Pauses, purple nodes are Jev decisions and grey nodes are plain code. Exact caps (re-asks, attempts, revisions) are set in the LLDs. ([Graph shape](../.scratch/talent-scout-hld/issues/06-graph-shape.md))

```mermaid
flowchart TD
  START([START])
  END_([END])
  intake[intake · parse request, load prefs]
  clarity_check[clarity_check · Jev ambiguity + LLM drafts questions]
  clarify[/clarify · PAUSE 1/]
  plan[plan · LLM search plan]
  plan_review[/plan_review · PAUSE 2/]
  fetch_agent[fetch_agent · LLM with bound tools]
  tools[tools · custom executor]
  collect[collect · dedupe, store]
  relevance[relevance · Jev per posting]
  broaden[broaden · LLM revises plan]
  low_data_review[/low_data_review · PAUSE 3/]
  batch_extract[batch_extract x N · LLM]
  normalise_skills[normalise_skills · LLM]
  stats[stats · python]
  write_brief[write_brief · LLM structured output]
  critic[critic · Jev per insight]
  render[render · JSON + Markdown]

  subgraph outside [outside the graph]
    gw[(Jobs Data Gateway · L1 cache, L2 store, budget guard)]
  end

  START --> intake --> clarity_check
  clarity_check -.->|"clear, or re-ask cap hit"| plan
  clarity_check -.->|"ambiguous"| clarify
  clarity_check -.->|"unusable at the cap"| END_
  clarify --> intake
  plan --> plan_review
  plan_review -.->|"approve / edit"| fetch_agent
  plan_review -.->|"reject + feedback"| plan
  plan_review -.->|"abort"| END_
  fetch_agent -.->|"has tool_calls"| tools
  fetch_agent -.->|"no tool_calls"| collect
  tools --> fetch_agent
  tools <-.-> gw
  collect --> relevance
  relevance -.->|"enough: Send x N"| batch_extract
  relevance -.->|"too few, attempts left"| broaden
  relevance -.->|"attempts exhausted, or no more data to get"| low_data_review
  broaden --> fetch_agent
  low_data_review -.->|"broaden"| broaden
  low_data_review -.->|"continue: Send x N"| batch_extract
  low_data_review -.->|"continue with 0 postings"| stats
  low_data_review -.->|"abort"| END_
  batch_extract -->|"reducer merges"| normalise_skills
  normalise_skills --> stats
  stats --> write_brief --> critic
  critic -.->|"unsupported, revisions left"| write_brief
  critic -.->|"supported, or revision cap hit"| render
  render --> END_

  classDef pause fill:#fde7c8,stroke:#d9822b,color:#000
  classDef jev fill:#e6defc,stroke:#6b4fd8,color:#000
  classDef code fill:#ececec,stroke:#888,color:#000
  class clarify,plan_review,low_data_review pause
  class clarity_check,relevance,critic jev
  class intake,collect,stats,render,tools code
```

- The `continue with 0 postings → stats` edge exists because a `Send` fan-out with zero branches never reaches `stats`. Without the edge, the Run would stall silently.
- A Run gets 3 Attempts (2 broadens) before `low_data_review`, where each further broaden is the user's choice. It skips straight there when Adzuna's budget is out or every search failed. ([Collection LLD](lld/collection.md) §4, §7)
- A vague answer to a Clarifying Question is re-asked at most once. After that, the Run proceeds and records an Assumption, unless there is no readable role or the country has no source, which ends the Run. ([Request & Plan LLD](lld/request-plan.md) §5)
- **Tool execution** uses a custom executor node: it reads `tool_calls`, dispatches each by name and returns `ToolMessage`s. The prebuilt `ToolNode` is not used, to insulate the graph from churn in LangChain's internals. Research confirmed that churn: `create_react_agent` is deprecated and `langchain` no longer re-exports `ToolNode`. ([Jobs sources and tool execution](../.scratch/talent-scout-hld/issues/03-jobs-sources-and-tool-execution.md), [LangGraph persistence research](../.scratch/talent-scout-hld/issues/15-research-langgraph-persistence-and-resume.md))

## 5. LLM vs code

([What does the LLM do versus code?](../.scratch/talent-scout-hld/issues/05-llm-extracts-code-computes.md))

- **The LLM extracts per-Posting facts**: skills as written, seniority, must-have vs nice-to-have, years of experience, employer type. Code drops any skill or year not found in the Posting's text. A single later LLM call groups skill spellings across Batches. ([Analysis LLD](lld/analysis.md) §6, §7)
- **Python computes every number**: counts, salary median and middle 50%, pay-disclosure share, top employers, posting-date trend. `stats` is a fixed node, not a tool. There is no decision for a model to make there, and a tool would add nondeterminism, tokens and a failure mode.
- **Pay stays in three separate groups**: advertised, Adzuna-estimated and federal are never pooled. All 100 Adzuna salaries in the fixtures are estimates. ([Analysis LLD](lld/analysis.md) §9)
- The brief writer receives the precomputed stats and Posting IDs. It chooses and phrases Insights but never invents figures.
- **Sufficiency** is a rule (count of Relevant Postings vs the Search Plan's target, with capped attempts), not an LLM opinion.

**LLM tiers**: every LLM call goes through OpenRouter. A cheaper tier handles batch extraction and question drafting; a stronger tier handles planning, brief writing and critique. Each tier has a `.with_fallbacks()` chain. When structured output is malformed, the call is retried with the validation error fed back, then falls back to the next model. The models themselves are chosen in LLD. ([LLM tiering and fallbacks](../.scratch/talent-scout-hld/issues/08-llm-tiering-and-fallbacks.md))

**Prompt caching** is a rule for building prompts, not a component: stable instructions and the schema come first, so batch calls share a cached prefix.

## 6. Jev placements

Jev is used only for semantic judgements that cannot be computed. ([Jev placement](../.scratch/talent-scout-hld/issues/07-jev-placement.md))

1. **Clarity check**: is the role, location or seniority too ambiguous to search on? This decides between clarifying and skipping ahead. An LLM still drafts the questions themselves.
2. **Posting relevance**: is this Posting really the researched role, or a keyword collision? Only Relevant Postings count toward Sufficiency.
3. **Critic** (stretch): is each Insight supported by the Postings it cites? This drives the revise loop.

All thresholds live in one place (the Kernel) and are tuned per model, because Jev's calibration does not transfer between models.

**Access**: `typesafe/jev-1.14` on OpenRouter returns full Noul, Choice and Score probabilities. `TypeSafeClassifier` works unchanged when pointed at OpenRouter's `base_url`, using the same OpenRouter key as the LLMs. Keep each request under about 32 KB, since longer inputs switch Jev to a slower, less accurate mode; this matters most for the critic. Fallback order if that fails: the OpenRouter decisions endpoint → TypeSafe directly → an LLM with structured output (which loses the probability distributions). ([Jev on OpenRouter research](../.scratch/talent-scout-hld/issues/12-research-jev-on-openrouter.md))

## 7. Jobs Data Gateway

The gateway sits outside the graph, between the tools and the APIs, and protects a small daily Adzuna quota. ([Gateway caching and expiry](../.scratch/talent-scout-hld/issues/04-jobs-data-gateway-caching-and-expiry.md))

- **L1 exact-query cache**: maps a normalised query, per source, to its mapped Postings. After 24 hours a row is refetched rather than served, and it is deleted only once every Posting in it has closed. This makes repeat runs, tests and replay free. Must-have. ([L1 cache, budget guard and replay](../.scratch/gateway-lld/issues/04-l1-cache-budget-guard-and-replay.md))
- **L2 region × Domain Posting store** (built later): every Adzuna Posting is stored, deduplicated by source ID. USAJOBS isn't stored, because its calls are free. On an L1 miss, the gateway skips the API call if L2 can fill the requested page with fresh Postings matching the region, Domain and role, reusing a Posting only for a query no broader than the one that found it. L2 also serves whatever it has when a live call fails. ([L2 store, expiry and sweep](../.scratch/gateway-lld/issues/07-l2-store-expiry-and-sweep.md))
- **Expiry**: hard expiry applies when the source gives a close date that has passed (USAJOBS `ApplicationCloseDate`). Soft expiry applies 7 days after Adzuna last returned a Posting. Adzuna has no expiry field, so its Postings only ever soft-expire, and every Adzuna search passes `max_days_old`. Expired rows are filtered out on read, and a sweep after each live write purges them, so cache hits do no sweep work.
- **Budget guard**: counts calls per source and refuses before the limit. Adzuna's limit is 25 calls a day, from the account dashboard. USAJOBS publishes no firm quota, so its calls are counted but not limited.
- **Replay mode**: the whole graph runs from cached responses. This doubles as the test harness.
- **Adzuna aggregates are excluded**: `histogram`, `top_companies`, `history` and the search `mean` carry no Posting IDs and don't feed the Market Brief. A source's match count may appear only as labelled sampling disclosure. ([Adzuna aggregate endpoints](../.scratch/gateway-lld/issues/06-adzuna-aggregate-endpoints.md))

Source facts that shape the design ([Adzuna research](../.scratch/talent-scout-hld/issues/13-research-adzuna-api-facts.md), [USAJOBS research](../.scratch/talent-scout-hld/issues/14-research-usajobs-api-facts.md)):
- **Adzuna**:
  - Salaries are in local currency with no stated period.
  - `salary_is_predicted` marks salaries Adzuna estimated itself.
  - Descriptions are truncated to 500 characters, so skills Evidence comes from snippets.
  - Commercial use beyond a 14-day evaluation needs a licence.
- **USAJOBS**:
  - Federal roles only.
  - Up to 500 results per page.
  - Pay comes with rate-interval codes.
  - Federal pay comes from fixed pay tables, so it must never be mixed unlabelled into market salary stats.

## 8. Pauses and durable resume

Being able to close the client at any Pause and resume exactly there is non-negotiable. ([Persistence and durable resume](../.scratch/talent-scout-hld/issues/10-persistence-and-durable-resume.md), [LangGraph persistence research](../.scratch/talent-scout-hld/issues/15-research-langgraph-persistence-and-resume.md))

- **Backend**:
  - The SQLite checkpointer stores threads. `SqliteStore`, in the same file, stores long-term preferences from pass 6.
  - Its known limit is a single writer: fine for the CLI, and replaced in the infra phase (Postgres is the candidate).
  - `MemorySaver` was rejected because its state dies with the process.
- **Durability**:
  - The Run Controller passes `durability="sync"` on every graph call. The default `async` mode can roll a just-answered Pause back.
  - Checkpoints are written per super-step, so parallel `batch_extract` branches share one.
- **Pause nodes are pure**:
  - Each Pause node makes exactly one `interrupt()` call, never inside `try/except`, and only writes the answer.
  - Anything generative, such as drafting questions, happens in the node before. The paused node re-runs from the top when resumed.
- **Returning re-shows the same Pause**: the Run Controller loads the thread, reads the pending payload from `get_state(...).interrupts`, re-displays it and resumes with `Command(resume=answer)`.
- **Run registry**: a plain `runs` table in the same file records thread, request summary, status and last-updated time. It's an index: the checkpoint is the truth, and disagreements reconcile on read. `scout resume` lists the resumable Runs, and Streamlit keeps the thread ID in the URL. ([Run Controller API and wiring](../.scratch/runtime-lld/issues/02-run-controller-and-wiring.md))
- **Concurrent resume guard**: LangGraph does not stop two processes from resuming the same thread at once, so the Run Controller does.
- **Kill mid-node**: only that node re-runs, and any repeated fetches are served from the L1 cache at no quota cost.

## 9. Tracing and Run Notes

LangSmith traces everything. Separately, the graph keeps a `run_log` in state: routing decisions with reasons, Clarifying Questions and answers, the final Search Plan and Assumptions. The `run_log` feeds the Market Brief's Run Notes and the `samples/` transcripts, so evaluators can follow a Run without access to LangSmith. ([Tracing and run log](../.scratch/talent-scout-hld/issues/11-tracing-and-run-log.md))

## 10. Infra topology (future phase)

```mermaid
flowchart LR
  subgraph core [Core · built now]
    cli[CLI] --> rc
    st[Streamlit] --> rc
    rc[Run Controller] --> g[Graph] --> gw[Jobs Data Gateway]
    rc --> db[(SQLite)]
  end
  subgraph shell [Infra shell · future phase, on MiniStack]
    api[API] --> q[[Queue]] --> w[Workers]
    sweep[Scheduled expiry sweep]
  end
  w --> rc
  sweep -.-> gw
```

- The core graph never depends on the infra shell. The shell wraps the core only through the Run Controller, which makes it an addition rather than a rewrite. ([Build priority order](../.scratch/talent-scout-hld/issues/02-build-priority-order.md), [Client surfaces and the Run Controller](../.scratch/talent-scout-hld/issues/09-client-surfaces-and-run-controller.md))
- In this phase, the expiry sweep also runs as a scheduled job, and persistence moves off SQLite.
- The infra shell's own LLD decides the API surface, queue technology, worker model, threading vs async, how concurrent Runs share the daily Adzuna budget, and the web UI.

## 11. Build order

Requirement tiers come in priority order ([Build priority order](../.scratch/talent-scout-hld/issues/02-build-priority-order.md)): must-have → recommended → streaming → infra shell → critic → long-term memory.

Each component's LLD covers all of its tiers, but the build goes in **passes across components**, not one finished component at a time. ([Component breakdown and build order](../.scratch/talent-scout-hld/issues/16-component-breakdown-and-build-order.md))

1. **Must-have walking skeleton**: Kernel → Gateway (L1, budget guard, replay, Adzuna) → Runtime + CLI (SQLite and the Pause protocol from day one) → Request & Plan (clarify only) → Collection → Analysis (with its Send fan-out, [Analysis LLD](lld/analysis.md) §5) → Brief (no critic).
2. **Recommended**: `plan_review` and `low_data_review` Pauses, fallbacks, `--focus`, USAJOBS, Streamlit, Gateway L2.
3. **Streaming progress**: the Runtime event stream, rendered by the clients.
4. **Infra shell** (J).
5. **Critic pass** (F).
6. **Long-term memory** (I).

After that come the `samples/`, README and write-up, as a delivery task.

## 12. Deferred to component LLDs

| Component | Open questions |
|---|---|
| Brief | Rules for the Confidence Tag and the Hiring Outlook |
| Long-term memory | Which preferences are remembered, and whether they are learned or asked |
| Infra shell | Everything listed in §10 |
| Delivery | Choosing the three sample runs within the Adzuna budget |
