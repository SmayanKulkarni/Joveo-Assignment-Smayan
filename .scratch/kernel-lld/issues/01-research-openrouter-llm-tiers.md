# Research: OpenRouter models for the LLM tiers

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by:
Findings: branch `research/openrouter-llm-tiers` (commit `d9681f5`), file `research/openrouter-llm-tiers.md`

## Question

Which OpenRouter models are realistic candidates for the Kernel's two LLM tiers, and how does LangChain reach them?

- **Cheap tier** (per-Posting batch extraction, Clarifying Question drafting; high volume) and **strong tier** (Search Plan, brief writing, critique): 2–3 candidates each with current input/output price, context length, and a sensible fallback partner from a different provider.
- Structured output support per candidate on OpenRouter: native `json_schema` response format vs tool calling only; how reliable each is; OpenRouter's `require_parameters` / provider routing to avoid providers that drop the schema.
- Prompt caching on OpenRouter per candidate provider (automatic vs `cache_control`), minimum prefix size, and the discount.
- LangChain connection: `ChatOpenAI(base_url="https://openrouter.ai/api/v1")` vs the `langchain-openrouter` package (does it exist, is it maintained, what does it add). Which one keeps `with_structured_output` and `.with_fallbacks()` working.
- Rate limits / credits behaviour that would affect a batch fan-out of ~50–200 parallel calls.

## Answer

Full findings on branch `research/openrouter-llm-tiers` (commit `d9681f5`), file `research/openrouter-llm-tiers.md`. Sourced from OpenRouter's live models/endpoints APIs, docs and package source; no live call (the worktree had no `.env`), so the [smoke test](04-live-smoke-test-openrouter-jev-langsmith.md) confirms.

- **Cheap tier candidates**: `openai/gpt-6-luna` → fallback `anthropic/claude-haiku-5.5` (both $0.10/$0.50 per M, ~1M ctx); reserve `google/gemini-3.1-flash-lite` ($0.25/$1.50).
- **Strong tier candidates**: `anthropic/claude-sonnet-5.5` → fallback `openai/gpt-6.1-sol` (both $2/$10, ~1M ctx); reserve `google/gemini-4-argon`. Most are under six weeks old: pin exact ids.
- **Structured output**: all support native `json_schema` on their first-party endpoint; not on Bedrock/AWS for Claude or Bedrock for gpt-6.1-sol, so set `require_parameters: true`. Claude 5.5 endpoints report forced tool choice unsupported, so use `method="json_schema", strict=True` explicitly (metadata-based, unverified live).
- **Prompt caching**: OpenAI/Gemini automatic (OpenAI min 1,024 tokens); Claude needs top-level `cache_control`, min 512 tokens on 5.x. Use endpoint-API prices, not the stale docs. Cheap tier input is ~$0.02/run, so caching only pays off in the strong tier's critique loop.
- **LangChain**: `langchain-openrouter` (`ChatOpenRouter` 0.2.9), the official package; keeps per-call cost and provider name, which `ChatOpenAI` loses. `with_structured_output` and `.with_fallbacks()` work either way.
- **Fan-out limits**: no request-rate cap on paid models; the binding limit is the in-flight spend budget (402). The SDK doesn't retry 402/429, so the LLD needs `max_tokens` on every call, LangGraph `max_concurrency` (~20), `.with_retry()` for 429/in-flight 402, and a balance check via `GET /api/v1/key` before a Run.
