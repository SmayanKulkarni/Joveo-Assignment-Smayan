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
- [Research: Adzuna API facts](issues/13-research-adzuna-api-facts.md): no expiry field (soft expiry + `max_days_old`), per-country categories endpoint, local-currency salaries with unstated period, descriptions truncated to 500 chars, quota unconfirmed (check dashboard), commercial-use licence caveat.
- [Research: LangGraph persistence and resume semantics](issues/15-research-langgraph-persistence-and-resume.md): SqliteStore exists; durable resume needs `durability="sync"`; one `interrupt()` per Pause node; registry in a Store namespace; Run Controller must guard concurrent resumes; ToolNode churn supports the custom executor.
- [Research: USAJOBS API facts](issues/14-research-usajobs-api-facts.md): 3-header auth, 500/page, salary with rate-interval codes, close date present (hard expiry works); federal-only, and its pay-table salaries must not mix unlabelled into market stats.
- [Component breakdown and build order](issues/16-component-breakdown-and-build-order.md): 10 concern-cut components (Kernel, Gateway, Request & Plan, Collection, Analysis, Brief, Runtime, Clients, Long-term memory, Infra shell); slices declared in Kernel, owned per stage; built in tier passes, must-have walking skeleton first.
- [Assemble docs/HLD.md](issues/17-assemble-hld-doc.md): written at [docs/HLD.md](../../docs/HLD.md); map destination reached.

## Not yet specified

_Empty: the component breakdown settled state ownership and handed the remaining fog to component LLDs (see Out of scope)._

## Out of scope

- Supervisor multi-agent setup (assessment stretch goal): not on the user's requirement list; may be revisited as a separate effort.
- LLD-level questions handed to their component's own LLD effort by [Component breakdown and build order](issues/16-component-breakdown-and-build-order.md), since the destination stops at the HLD:
  - **Analysis**: currency/period normalisation (Adzuna local currency with no stated period, USAJOBS `RateIntervalCode`, `salary_is_predicted`), multi-source stats (USAJOBS pay tables vs Adzuna), batching for Samples over 500 (snippet-based skills evidence is a known write-up limitation).
  - **Brief**: Confidence Tag and Hiring Outlook rules.
  - **Jobs Data Gateway**: whether Adzuna histogram / top_companies / history feed the brief (no Posting IDs, so not strict Evidence).
  - **Request & Plan + Clients**: which nodes or prompts each `--focus` flag changes.
  - **Runtime**: streaming event model.
  - **Long-term memory**: which preferences are remembered, learned vs asked.
  - **Infra shell**: API surface, queue on MiniStack, worker model, threading vs async, shared daily Adzuna budget across concurrent Runs, persistence migration off SQLite, web UI.
  - **Delivery task**: sample-run strategy for the three `samples/` requests within the Adzuna budget.
