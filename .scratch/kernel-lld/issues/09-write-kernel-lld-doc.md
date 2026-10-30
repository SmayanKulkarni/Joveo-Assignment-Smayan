# Write docs/lld/kernel.md

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by: 05, 06, 07, 08

## Question

Write `docs/lld/kernel.md` from the resolved tickets and the map's Notes (layout, Pydantic-everywhere, scope rules): module layout, shared domain types, state schema + reducers, `run_log`, LLM tier factory, Jev wrapper + thresholds, settings, tracing, test seams, and the build checklist for the walking skeleton. Gist and link each decision to its ticket; introduce no new decisions.

Input from [State schema, reducers and run_log](06-state-schema-and-run-log.md): the doc should note that Run Notes are built from `run_log` plus state slices, which narrows HLD §9's wording, and link [docs/lld/future-scope.md](../../../docs/lld/future-scope.md).

Working notes so far: `docs/lld/kernel-notes.md`. Build the final doc from them once the LLM tier factory ticket closes.

## Answer (2026-10-30)

Written at [docs/lld/kernel.md](../../../docs/lld/kernel.md). The working notes were turned into the final doc and removed, so there's one source. §12 (LLM tier factory), §13 (settings), §14 (replay cache), §15 (test seams) and §16 (pass-1 build checklist) are new. §9 gained the Caveat kind and its render rule. Items marked ⏳ belong to a named stage or Runtime LLD, not the Kernel. Future-scope gained the production tier models and Claude `cache_control`.
