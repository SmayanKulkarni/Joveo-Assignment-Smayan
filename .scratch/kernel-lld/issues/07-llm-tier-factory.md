# LLM tier factory

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01, 02, 04

## Question

What is the Kernel's LLM tier factory: its interface, models, fallbacks and failure policy?

- **Interface** stages call (e.g. a tier name → chat model; a tier + schema → structured runnable), and what stays out of it (prompts belong to stages).
- **Model picks**: primary + fallback chain for the cheap and strong tiers, from the OpenRouter research.
- **Validation retry**: how many retries with the validation error fed back before falling to the next model; what's raised when the chain is exhausted and how the node should treat it.
- **Prompt-prefix rule** (HLD §5): how the factory or a helper enforces stable instructions + schema first so batch calls share a cached prefix.
- **Tracing**: `run_name`, tags (tier, model) and metadata on every tier call.
- **Test seam**: how tests and replay substitute a fake model without touching stage code.
- Cost/token accounting, if any, beyond LangSmith.

Input from [Live smoke test: OpenRouter LLM, Jev and LangSmith](04-live-smoke-test-openrouter-jev-langsmith.md): `ChatOpenRouter` runs trace in LangSmith **without cost**, so the cost/token accounting point is live. Also, structured-output calls nest about 10 chain runs, so set `run_name` and tags on the outer runnable.

Input from [Jev wrapper and thresholds](08-jev-wrapper-and-thresholds.md): Jev's last fallback hop is an LLM adapter on the **cheap** tier. It needs a structured-output call returning `{question_id: {answer: bool, reason: str}}`, so the factory must give it a tier + schema → structured runnable.

## Answer (2026-10-30)

Grilled with the user, with a live check of the new models (about $0.0002 spent). The factory lives in `kernel/llm.py`, with `kernel/settings.py` and `kernel/replay.py` beside it.

- **Interface**: a `Tiers` object with two async entry points.
  - `tiers.structured(tier, Schema, *, system, name, max_tokens=None) -> Runnable[str, Schema]` serves intake, plan, extraction, brief writing, the critic and Jev's LLM fallback. `system` is fixed at build time and the input is only the variable user content, so the HLD's prompt-prefix rule (stable instructions and schema first) is enforced by the signature, with no helper.
  - `tiers.chat(tier, *, tools, name, max_tokens=None) -> Runnable[list[AnyMessage], AIMessage]` exists only for `fetch_agent`. Tools are bound to each model *before* `with_fallbacks`, because `RunnableWithFallbacks` has no `bind_tools`.
  - Async-only, to match `jev.judge`. Claude `cache_control` is left out, since caching only pays off in the critic loop (future-scope).
- **Models (testing phase)**: both `cheap` and `strong` run `deepseek/deepseek-v4.1-flash` ($0.045/$0.50 per M) → `minimax/minimax-m3.1-flash` ($0.15/$0.60), two providers, 1M context, both with strict `json_schema` under `require_parameters: true`. The tier names stay in code, so one `.env` change (`LLM_CHEAP=a,b`, `LLM_STRONG=a,b`) restores the research picks, which are parked in future-scope as production defaults.
- **Reasoning and output room**: every call sends `reasoning: {effort}`, `low` for cheap and `medium` for strong, both overridable in settings. Live, DeepSeek at default effort spent 178 of 200 output tokens reasoning on a 3-field extraction. MiniMax refuses `reasoning.enabled: false` (400, "Reasoning is mandatory"), but `effort: "low"` gave clean JSON on both with 0 reasoning tokens. `max_tokens` defaults to 2,048 (cheap) and 8,192 (strong), overridable per call, and settings refuse anything below 1,000. It is a ceiling, not a charge. Worst case, with every call using ~1,000 output tokens, is about $0.12 per heavy Run against about $0.02 at low effort.
- **Transport failures**: each model is wrapped in `with_retry` (3 attempts, jittered backoff, on 429, 5xx, timeouts, connection errors and 402, since a 402 is usually in-flight spend that clears), then `with_fallbacks` to the next model with an explicit exception list. It never falls back on 400, 401 or 422 (our bug) or 402 (same account). 60 s timeout per call.
- **Validation retry**: the factory parses the response itself (`Schema.model_validate_json` on the raw content) instead of trusting `with_structured_output`'s parser, which raises inside the call and loses the raw output. On a `ValidationError` it resends the same prompt plus the bad output as an `AIMessage` and a `HumanMessage` carrying the Pydantic error text and "return corrected JSON". **One feedback retry per model**, so at most 4 attempts per call over the 2-model chain.
- **Chain exhausted**: raises `LLMExhausted(tier, name, attempts)`, chained to the last error. Nodes don't catch it by default: the Run stops at that node, the checkpoint stays at the last committed step, and `--resume` reruns only that node. A stage may catch it where losing one item is acceptable (e.g. Analysis skipping one Posting), and must then log a Caveat.
- **Transparency (Caveat)**: a new glossary term and a new `LogKind.caveat` in `run_log`, written with `log()`, with optional `dimension` and `posting_keys` in `data`. Brief must render every Caveat in Run Notes; `warning` and `note` stay internal. Stages decide when to raise one, and each stage LLD lists its Caveats. Backend errors (a Run killed by `LLMExhausted`, a 401, a bug) are never Caveats: the CLI shows "Run stopped at <node>, resume with `--resume`", and the details go to logs and LangSmith. A successful LLM fallback isn't shown either, because the fallback's output passes the same schema validation and can't change a job-related conclusion. LLM failures reach the user only through their effect: a skipped Posting, or Jev falling back to the LLM (judged without probabilities). Both are Caveats.
- **Concurrency and balance**: one process-wide `asyncio.Semaphore(20)` inside the factory (size from settings), so Runtime doesn't need LangGraph's `max_concurrency`. The Kernel exports `check_balance(settings)` (`GET /api/v1/key`). The Run Controller calls it before starting or resuming a Run and refuses below a floor (default $0.25).
- **Cost**: the factory copies OpenRouter's `response_metadata["cost"]` into the LLM run's `usage_metadata` cost fields so LangSmith shows the exact cost. Which field LangSmith reads gets confirmed at build; the fallback is LangSmith model prices for the pinned ids. No cost in `run_log`.
- **Tracing**: the outer runnable gets `run_name=f"llm:{name}"`; each model is tagged `tier:<tier>` and `model:<id>` before wrapping; metadata carries `tier`, `name` and the copied cost. The structured runnable returns only the `Schema` instance. Which model answered and how many retries ran is visible only in LangSmith.
- **Test seam**: constructor injection, `Tiers(chains: dict[Tier, list[BaseChatModel]], settings)`. `make_tiers(settings)` builds the real `ChatOpenRouter` chains. Tests pass langchain-core's `GenericFakeChatModel` with canned JSON strings, which runs the real parse, feedback-retry and fallback code. A few-line fake subclass whose `bind_tools` returns itself covers `chat()`. No custom fake framework.
- **Replay recording** (resolves the map's open item): `kernel/replay.py`, off by default, switched on by `REPLAY_CACHE=<path>` and shared with the Gateway's replay switch.
  - LLM: a ~25-line `BaseCache` on stdlib `sqlite3`, passed to `set_llm_cache()`. It is keyed on messages + model id + params, so prompt edits, model changes and feedback retries all miss correctly. Writing it avoids the `langchain-community` dependency.
  - Jev: ~20 lines in `jev.judge`, keyed on (model chain, hash of the request JSON), in the same SQLite file.
  - A replayed Run is made obvious. `render` puts a replay banner at the top of the Market Brief, read from settings. Collection logs a Caveat with the age of the oldest cached jobs response used, because replay ignores L1's TTL.
  - Built in pass 2, not the walking skeleton. Since LLM and Jev now replay too, HLD §7's "the whole graph runs from cached responses" holds as written.
- **Settings**: `kernel/settings.py`, one `Settings(BaseSettings)` (adds `pydantic-settings`) read from the root `.env`. It holds keys, tier chains, reasoning efforts, `max_tokens` defaults, semaphore sizes, the balance floor, the LangSmith project and `REPLAY_CACHE`. `get_settings()` is cached, and on first load it exports the LangSmith env vars to `os.environ` before any LangChain call reads them. `make_jev(settings)` and `make_tiers(settings)` take the same object.
