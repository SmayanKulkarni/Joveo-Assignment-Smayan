# Kernel LLD

Label: wayfinder:map
Parent: [Talent Market Scout: HLD](../talent-scout-hld/map.md) (component A in [docs/HLD.md](../../docs/HLD.md) §3)

## Destination

`docs/lld/kernel.md`: an LLD of the Kernel precise enough to build straight from (shared domain types, state schema + reducers, `run_log`, LLM tier factory, Jev wrapper + thresholds), with nothing left to decide. Building the code is a separate effort after this map.

## Notes

- Domain: the Kernel is the first thing built in the must-have walking skeleton; every other component imports it. Vocabulary: `GLOSSARY.md`. Spec: `Joveo_Talent_Market_Agent- Assessment.pdf`. Deadline Mon 2 Nov 2026, 9:00 AM.
- Skills: `langchain-router` first for any framework question (per `CLAUDE.md`), then what it names (likely `langgraph-fundamentals`, `langgraph-persistence`, `langchain-middleware`); `langgraph-decision-models` for Jev; `grilling` + `domain-modeling` for grilling tickets.
- Scope rules (decided at charting):
  - **Shared contract only.** The Kernel fixes cross-component domain types, every state slice's key + owner + reducer, and `run_log`. Stage-private fields are added to the Kernel's schema file by that stage's own LLD.
  - **Jev split.** Kernel owns the classifier wrapper, threshold config (per model, per placement), first-cut values + tuning procedure, fallback chain. Stages own their criteria/labels.
  - **LLM tiers.** Model picks, fallback chains and validation-retry policy are decided here.
  - **LangSmith.** Kernel owns tracing settings, run names/tags on LLM tier calls, and making Jev calls traceable. Per-Run metadata (thread, request) belongs to Runtime.
- Standing preferences (decided at charting):
  - **Pydantic v2 everywhere**: domain types *and* the graph state schema (`BaseModel` with `Annotated` reducers), not `TypedDict`.
  - **Layout/tooling**: `uv`, Python 3.12, `src/talent_scout/` package with `kernel/` as first subpackage, `pytest`, settings loaded from root `.env` (OpenRouter, Adzuna, USAJOBS, LangSmith keys).
  - Live calls through the `.env` OpenRouter key are fine for smoke tests (cents, not dollars).

## Decisions so far

<!-- one line per closed ticket -->

- [Research: OpenRouter models for the LLM tiers](issues/01-research-openrouter-llm-tiers.md): cheap gpt-6-luna → haiku-5.5, strong sonnet-5.5 → gpt-6.1-sol; `ChatOpenRouter` with `json_schema` strict + `require_parameters`; binding limit is in-flight spend (402), so cap concurrency and retry.
- [Research: LangGraph/LangChain contract for Pydantic state](issues/02-research-langgraph-pydantic-state-contract.md): Pydantic state works on langgraph 1.2.x if nodes return partial dicts, `Send` payloads are models, writes are validated by us, and `LANGGRAPH_STRICT_MSGPACK` is on; structured-output failures surface differently per mode, so retry is ours; fallbacks compose.
- [Research: langchain-typesafe API surface](issues/03-research-langchain-typesafe-api.md): alpha 0.0.1a3 Runnable, one request per Posting, `abatch` needs `max_concurrency`; already traced in LangSmith (cost/id via an HTTP hook); explicit fallback exception list; set the timeout and size-check inputs yourself.
- [Live smoke test: OpenRouter LLM, Jev and LangSmith](issues/04-live-smoke-test-openrouter-jev-langsmith.md): live calls work as the research predicted; `json_schema` beats `function_calling` (cheaper, steadier); Jev's id and cost come back only through an HTTP hook, but LangSmith traces and prices Jev on its own; `ChatOpenRouter` runs trace without cost, so the Kernel supplies it.
- [Jev wrapper and thresholds](issues/08-jev-wrapper-and-thresholds.md): Noul-only `judge(placement, state, questions)` returning `Judgement`s; one cut per (model, placement), all 0.5 until a JSONL sweep tunes them, no uncertain band; jev-1.14 with retry → cheap LLM tier (bool + reason); truncate longest field to 30 KB; global semaphore of 8; no HTTP hook; injected classifier + `fake_classifier` for tests.
- [Shared domain types](issues/05-shared-domain-types.md): Kernel holds only cross-boundary types (Posting, Evidence, HiringRequest, Clarifying Question, Assumption, Search Plan, Market stats as a flat list of Stats with ids); the Gateway maps raw JSON to Postings keyed `source:source_id`; a type doubles as an LLM schema only when the model fills every field.
- [State schema, reducers and run_log](issues/06-state-schema-and-run-log.md): one flat frozen Pydantic `State` in `kernel/state.py`; every slice `LastValue` except `extractions` (merge, for the `Send` fan-out); `broaden` appends to Collection's `broadened_plans` (attempts = its length, `current_plan` derived) and resets `messages`; `run_log` is narrative only, no timestamps, appended via `log()`; an `owned(node, owner)` guard validates every write, owner and `Send` payload.
- [LLM tier factory](issues/07-llm-tier-factory.md): async `Tiers.structured` (system fixed at build, so the prefix rule is the signature) + `chat` for `fetch_agent`; both tiers DeepSeek v4.1 Flash → MiniMax M3.1 Flash while testing, reasoning `low`/`medium`, `max_tokens` 2,048/8,192 (floor 1,000); we parse, 1 feedback retry per model, `LLMExhausted` propagates; new **Caveat** `run_log` kind that Brief must render, backend errors never shown; semaphore 20, `check_balance`, cost copied into LangSmith; injected chains + `GenericFakeChatModel`; SQLite replay cache for LLM and Jev behind `REPLAY_CACHE` (pass 2), with a replay banner.
- [Write docs/lld/kernel.md](issues/09-write-kernel-lld-doc.md): written at [docs/lld/kernel.md](../../docs/lld/kernel.md), replacing the working notes; adds settings, replay, test seams and the pass-1 build checklist.

## Not yet specified

_Empty: the LLM tier factory ticket settled replay for LLM and Jev calls (a SQLite replay cache behind `REPLAY_CACHE`, shared with the Gateway). Map destination reached at [docs/lld/kernel.md](../../docs/lld/kernel.md)._

## Out of scope

- Final calibrated Jev threshold values: need live labelled runs; this map stops at first-cut values + the tuning procedure.
- Stage-private state fields and each stage's Jev criteria text: owned by that stage's LLD.
- Per-Run LangSmith metadata and `config` at invoke time: Runtime LLD.
- `SqliteStore` needing its own autocommit connection and JSON-dumped values (found by [Research: LangGraph/LangChain contract for Pydantic state](issues/02-research-langgraph-pydantic-state-contract.md)): Runtime LLD.
- Per-Posting extraction type and the Stat catalogue (Analysis LLD); Insight, Confidence Tag, Client Recommendation, Hiring Outlook and Market Brief types (Brief LLD): each is read only inside its own component, so [Shared domain types](issues/05-shared-domain-types.md) leaves them to those LLDs.
- Writing the Kernel code: separate build effort after this map.
- `preferences` state slice: Long-term memory LLD adds it (found by [State schema, reducers and run_log](issues/06-state-schema-and-run-log.md)).
- Deliberate deferrals (Jev Choice/Score, `jev-1.13` hop, per-call Jev ids, `run_log` timestamps, calibrated cuts) are tracked with their triggers in [docs/lld/future-scope.md](../../docs/lld/future-scope.md).
