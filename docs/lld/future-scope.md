# Future scope

Work deliberately left out of an LLD, with why and what would bring it back. One section per component. Items that simply belong to another component's LLD are not listed here; that LLD owns them.

## Kernel

| Item | Why it's left out | Brings it back |
|---|---|---|
| `preferences` state slice | Long-term memory is the last build pass and its LLD decides what preferences contain | Long-term memory LLD adds the slice to `kernel/state.py` |
| Calibrated Jev cuts | Need live labelled runs; every cut ships at 0.5, marked untuned | Running the `evals/jev/<placement>.jsonl` sweep and editing `thresholds.py` |
| Jev Choice and Score in the wrapper | All three placements are yes/no questions, so the wrapper is Noul-only | A stage that needs a multi-label or graded judgement |
| `jev-1.13` as a middle fallback hop | It would need its own tuned cuts | `jev-1.14` proving flaky in practice |
| OpenRouter generation id and cost per Jev call in `run_log` | LangSmith already traces and prices Jev; the HTTP hook costs the classifier's 30 s timeout | Needing per-call ids outside LangSmith |
| Timestamps on `run_log` entries | List order is event order, LangSmith has the times, and replay transcripts stay byte-identical | A consumer that needs wall-clock times without LangSmith |
| Production tier models: cheap `openai/gpt-6-luna` → `anthropic/claude-haiku-5.5`, strong `anthropic/claude-sonnet-5.5` → `openai/gpt-6.1-sol` | This is a testing project for now, so both tiers run DeepSeek v4.1 Flash → MiniMax M3.1 Flash | Leaving the testing phase: set `LLM_CHEAP` / `LLM_STRONG` in `.env` and re-run the live smoke script |
| Claude `cache_control` for prompt caching | Caching only pays off in the strong tier's critic loop, and the testing models cache automatically or not at all | The critic pass (5) running on a Claude strong tier |
