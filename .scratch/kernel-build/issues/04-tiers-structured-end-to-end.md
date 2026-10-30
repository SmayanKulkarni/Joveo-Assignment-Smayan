# 04: Tiers.structured, end to end

**What to build:** a stage can ask a tier for a validated Pydantic object and get one, from a real model through OpenRouter, with bad output corrected by feedback, transport failures retried and fallen back, and cost visible in LangSmith. If the chain runs out, the caller gets `LLMExhausted`. Spec: [Kernel LLD](../../../docs/lld/kernel.md) §12, §15, §16 steps 6-7.

Start of the live smoke script (not in CI), which ticket 06 also adds to. Live calls use `minimax/minimax-m3.1-flash` and spend cents.

**Blocked by:** 01: Project skeleton and settings.

**Status:** done

- [x] `Tiers(chains, settings)` takes injected chains, and `make_tiers(settings)` builds real `ChatOpenRouter` chains with strict `json_schema` and `require_parameters: true`
- [x] `structured` takes its `system` text at build time and only the variable user content as input
- [x] The factory parses raw content itself, and every call sends the tier's reasoning effort and `max_tokens`
- [x] Test: a bad-then-good fake response passes on the feedback retry, and the retry carries the bad output and the Pydantic error text
- [x] Test: two bad responses on one model reach the next model
- [x] Test: the chain running out raises `LLMExhausted` with `tier`, `name` and `attempts`, chained to the last error
- [x] Test: 429, 5xx, timeouts and connection errors are retried and then fall back; 400, 401, 422 and 402 never fall back
- [x] Test: concurrent calls never exceed the process-wide semaphore
- [x] Runs carry `run_name=llm:<name>`, each model is tagged `tier:<tier>` and `model:<id>`, and metadata carries `tier` and `name`
- [x] Live smoke: one `structured` call per tier returns a valid object and shows in the LangSmith project
- [x] Cost shows in LangSmith. Record which `usage_metadata` field it reads in LLD §12, or fall back to LangSmith model prices for the pinned ids and record that
