# Talent Market Scout: HLD

Label: wayfinder:map

## Destination

`docs/HLD.md` for the Talent Market Scout Agent (Joveo assessment, due Mon 2 Nov 2026, 9:00 AM) plus an ordered component breakdown, where each component becomes its own later LLD/build effort. No LLD or code decisions on this map.

## Notes

- Domain: LangGraph/LangChain agent (Python) that turns a Hiring Request into an evidence-backed Market Brief. Spec: `Joveo_Talent_Market_Agent- Assessment.pdf`. Vocabulary: `GLOSSARY.md`.
- Stack fixed by the user: Python, LangChain + LangGraph, OpenRouter for LLMs (models picked in LLD), LangSmith tracing, Adzuna (25 req/day) + USAJOBS keys in root `.env`, Jev (on OpenRouter) for probabilistic routing.
- Skills: `langchain-router` first for any framework question (per `CLAUDE.md`), then the skills it names; `langgraph-decision-models` for Jev; `grilling` + `domain-modeling` for grilling tickets.
- Standing preferences: the reference flow in the PDF is a suggestion, not a contract. Infra (API, queues, workers, threading, concurrency, MiniStack) is a future phase after core requirements. Durable resume at any Pause is non-negotiable.

## Decisions so far

- [What does the HLD cover, and what is deferred to LLD?](issues/01-hld-destination-and-lld-deferral.md): HLD = components, graph shape, state ownership, infra topology, build order; field types, prompts, limits, models deferred to per-component LLD.
- [What is the build priority order?](issues/02-build-priority-order.md): must → recommended → streaming → infra shell (future phase) → critic → long-term memory.
- [Which jobs sources are used, and how are tools executed?](issues/03-jobs-sources-and-tool-execution.md): Adzuna primary, USAJOBS for US; `@tool`s run by a custom executor node instead of ToolNode.
- [How does the Jobs Data Gateway cache, budget and expire data?](issues/04-jobs-data-gateway-caching-and-expiry.md): L1 exact-query cache + L2 region × Domain Posting store, hard/soft expiry with filter-on-read and per-Run sweep, budget guard, replay mode.
- [What does the LLM do versus deterministic code?](issues/05-llm-extracts-code-computes.md): LLM extracts per-Posting facts; a separate `stats` node computes every number; Sufficiency is a rule.
- [What is the node-level graph shape?](issues/06-graph-shape.md): full mermaid graph with three Pauses, fetch/broaden loop, Send fan-out, critic loop, zero-Postings edge.
- [Where does Jev make routing decisions?](issues/07-jev-placement.md): clarity check, Posting relevance, critic.
- [How are LLMs tiered, and how are failures handled?](issues/08-llm-tiering-and-fallbacks.md): OpenRouter, tier concept + fallback chains, validation-error retry; models deferred.
- [Which clients exist, and how do they talk to the graph?](issues/09-client-surfaces-and-run-controller.md): CLI core, optional Streamlit, all via a Run Controller seam.
- [How is state persisted so a Run survives the user leaving?](issues/10-persistence-and-durable-resume.md): SQLite checkpointer + Store; pure Pause nodes, run registry, re-shown Pause payloads.
- [How are Runs traced and explained?](issues/11-tracing-and-run-log.md): LangSmith plus a run log in state feeding Run Notes and samples.
- [Research: Jev on OpenRouter](issues/12-research-jev-on-openrouter.md): `typesafe/jev-1.14` on OpenRouter returns full Noul/Choice/Score probabilities; `TypeSafeClassifier` works via `base_url`, same OpenRouter key; keep requests under ~32 KB.
- [Research: USAJOBS API facts](issues/14-research-usajobs-api-facts.md): 3-header auth, 500/page, salary with rate-interval codes, close date present (hard expiry works); federal-only, and its pay-table salaries must not mix unlabelled into market stats.

## Not yet specified

- **Infra shell internals**: API surface, queue technology on MiniStack (SQS?), worker model, threading vs async, how concurrent Runs share the Gateway's daily budget, persistence migration off SQLite (Postgres vs DynamoDB), web UI. Sharpens once the component breakdown fixes the Run Controller seam.
- **State ownership map**: which component reads/writes which slice of graph state. Falls out of the component breakdown.
- **Streaming event model**: what progress events exist and how one stream feeds CLI, Streamlit and later the API.
- **Currency and period normalisation**: where FX rates and hourly→annual conversion come from; depends on Adzuna/USAJOBS salary facts.
- **Multi-source stats**: how USAJOBS Postings (federal pay tables) sit alongside Adzuna Postings in compensation stats: separate, labelled, or excluded.
- **Confidence Tag and Hiring Outlook rules**: how thresholds are set and justified from evidence counts and stats.
- **`--focus` flags**: which nodes or prompts a focus changes.
- **Long-term memory contents**: which preferences are remembered, and when they are learned vs asked.
- **Batching for large Samples (>500)**: batch sizing against context limits; depends on posting description lengths.
- **Sample-run strategy**: picking the three `samples/` requests within the Adzuna budget.

## Out of scope

- Supervisor multi-agent setup (assessment stretch goal): not on the user's requirement list; may be revisited as a separate effort.
