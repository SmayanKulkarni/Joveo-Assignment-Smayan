# Live smoke test: OpenRouter LLM, Jev and LangSmith

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by:

## Question

Make one real call of each kind with the keys in root `.env`, so the tier factory and Jev wrapper are designed against observed behaviour rather than docs (the HLD research made no live call). AFK; spending a few cents is approved.

- One chat call through OpenRouter with structured output (a tiny Pydantic schema).
- One Jev Noul, one Choice and one Score call to `typesafe/jev-1.14` via `TypeSafeClassifier` with `base_url="https://openrouter.ai/api"`.
- Confirm both appear in the LangSmith project, and note whether the Jev call is traced at all.

Record: exact response shapes (redact nothing structural, no secrets), latency, `usage.cost`, any surprises. Throwaway script lives in the scratchpad, not the repo.

## Answer (2026-10-30)

Run with `langchain-openrouter` 0.2.9, `langchain-typesafe` 0.0.1a3, `langsmith` 0.14.16. The chat calls used `minimax/minimax-m3.1-flash`, the user's choice for tests, not the tier models. Total spend was about $0.0002.

**OpenRouter chat, structured output** (`require_parameters: true`, `strict=True`, `include_raw=True`):
- `json_schema`: 2.05 s, parsed cleanly, `finish_reason: stop`. 221 input / 27 output tokens, `usage_metadata.input_token_details.cache_read` = 128, cost $0.000032.
- `function_calling`: 1.63 s, parsed from `tool_calls`, `content` is empty. It used 114 reasoning tokens, so it cost 4.5x as much ($0.000146). Field values also drifted: "Data Engineer"/"senior" against "Senior Data Engineer"/"Senior" from `json_schema`. That supports making `json_schema` the default.
- `response_metadata` carries `id` (`gen-...`), `model_name`, `model_provider: "openrouter"`, `finish_reason`, `cost` and `cost_details`. It does **not** name the upstream provider. `usage_metadata` carries the cache-read and reasoning token counts.

**Jev** (`TypeSafeClassifier`, `base_url="https://openrouter.ai/api"`, one question per call):
- Noul 1.15 s, Choice 0.74 s, Score 1.10 s. Each costs about $0.000014 (roughly 330-360 input tokens).
- The resolved model is `typesafe/jev-1.14-20261014`. The shapes match the research: `noul: 0.98`; Choice has `choice`, `probabilities` and `confidence`; Score has `score: 2.0`, `legend` and `probabilities` keyed by int.
- The raw body has `id` (`gen-dec-...`), `provider: "TypeSafe"` and `usage.cost`. The classifier drops all three, and `request_id` is `null` because OpenRouter doesn't send `x-typesafe-request-id`. Headers include `x-generation-id`, which equals the body `id`, and `x-provider-name`. **Confirmed: a response hook on an injected `httpx2.Client` gets both `id` and cost.**
- The probabilities on this easy input were saturated (1.0/0.0, confidence 1.0). Tuning thresholds needs harder examples.

**LangSmith**: traced once the key was fixed. The first run's 403 came from a stray extra character at the end of `LANGSMITH_API_KEY` in `.env`; the region and workspace were not the problem.
- Every call appears under the `@traceable` parent with no extra wiring. Jev shows as `TypeSafeClassifier`, `run_type: llm`, model `typesafe/jev-1.14`, with tokens **and cost**. LangSmith's cost exactly matches OpenRouter's `usage.cost`: it prices input tokens at $0.042/M and output at zero. **No `@traceable` and no custom model price are needed for Jev.**
- `ChatOpenRouter` shows as `run_type: llm` with tokens and model name, but **cost is empty**, even though `response_metadata.cost` has it. The Kernel has to supply chat cost itself (copy `response_metadata.cost` into run metadata or `usage_metadata`, or add LangSmith model prices for each tier model). The production tier models weren't tested, so it's unknown whether LangSmith already prices them.
- `with_structured_output(include_raw=True)` makes about 10 nested chain runs per call (`RunnableSequence`, `RunnableParallel`, `RunnableAssign`, parser), so `run_name` and tags belong on the outer runnable.

**Surprises**: the deprecation warning on `list_runs()` (use `client.runs.query()`), and the `TypeSafeClassifier` beta warning on every construction.
