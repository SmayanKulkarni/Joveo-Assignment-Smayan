# Research: langchain-typesafe API surface

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by:
Findings: branch `research/langchain-typesafe-api` (commit `0d5608a`), file `research/langchain-typesafe-api.md`

## Question

What does `langchain-typesafe`'s `TypeSafeClassifier` actually expose, so the Kernel's Jev wrapper can be designed against it? Builds on the HLD's [Research: Jev on OpenRouter](../../talent-scout-hld/issues/12-research-jev-on-openrouter.md) (OpenRouter access already confirmed).

- Current version; methods for Noul, Choice and Score; their argument and return types (where the probabilities, per-label distribution and confidence live).
- Async and batch support: can relevance check N Postings concurrently or in one request? Concurrency limits.
- Error types and which should trigger the fallback chain (OpenRouter decisions endpoint → direct TypeSafe → LLM structured output).
- Is it a LangChain `Runnable`, and does a call show up in LangSmith on its own, or does the wrapper need `@traceable`? Can `usage.cost` and the request id be recovered (the HLD research says the classifier drops them)?
- How input over ~32 KB is signalled or handled, and how to measure request size before sending.

## Answer

Full findings on branch `research/langchain-typesafe-api` (commit `0d5608a`), file `research/langchain-typesafe-api.md`. Sourced from the 0.0.1a3 package code, TypeSafe docs/OpenAPI and OpenRouter's reference; behaviour checked offline against a mocked HTTP layer, no live call. Unsettled points are marked unconfirmed in the file.

- **Surface**: `langchain-typesafe` 0.0.1a3 (alpha); `TypeSafeClassifier` (beta) is a Runnable with `invoke`/`ainvoke`, one `/v1/systemone` request each. Answers: `nouls[id].noul` (P(yes)), `choices[id]` (`choice`, `probabilities`, `confidence`), `scores[id]` (`score`, `probabilities`, `legend`, `confidence`). Error classes live in `langchain_typesafe.client` (the README's top-level import fails).
- **Concurrency**: one state per request, so N Postings means N requests. `abatch` is LangChain's generic version, unbounded unless `max_concurrency` is set. No built-in retries.
- **Errors → fallback**: retry then fall back on 429, 5xx (incl. 524/529), connection errors and timeouts; fall back on 402, 404 and malformed 200s. Never fall back on 400/422 (it fails everywhere). A 400 `max_tokens_exceeded` or a 413 means trim, not switch. 402/413/415 surface as plain `TypeSafeAPIError`, so `with_fallbacks` needs an explicit `exceptions_to_handle`.
- **Tracing**: already traced as an `llm` run with tokens, nested under the calling node, so no `@traceable` needed. Cost and request id are dropped but recoverable via a response hook on an injected HTTP client writing to run metadata; add a LangSmith model price for `typesafe/jev-1.14`.
- **Timeout trap**: an injected HTTP client ignores the classifier's 30 s timeout and falls back to 5 s, so set it explicitly.
- **Large input**: OpenRouter silently switches to long-context mode above ~32 KB. The classifier never checks size, so the wrapper measures `json.dumps(state, ensure_ascii=False, separators=(",", ":"))` and truncates before sending.
- **Research recommendation** (input to the Jev wrapper ticket, not yet a decision): one long-lived classifier with injected clients (timeout + cost/id hook), `abatch` with `max_concurrency` ~8, size check, retries and fallbacks from `with_retry`/`with_fallbacks`; skip the `/api/alpha/decisions` hop since it fails the same ways.
