# 08: Replay cache (pass 2)

**What to build:** with `REPLAY_CACHE=<path>` set, LLM and Jev calls replay from a SQLite file, so running the same calls twice makes no live calls the second time. Changing a prompt or model misses the cache and calls live. Unset, nothing changes. Spec: [Kernel LLD](../../../docs/lld/kernel.md) §11, §14.

Pass 2: not needed for the walking skeleton. Out of scope: Gateway replay of jobs data (Gateway reads the same setting), the replay banner (Brief) and the cached-data age Caveat (Collection).

**Blocked by:** 04: Tiers.structured, end to end; 06: Jev wrapper and thresholds.

**Status:** done

- [x] LLM replay is a small `BaseCache` on stdlib `sqlite3` installed with `set_llm_cache()`, with no `langchain-community` dependency
- [x] Jev replay is a second table in the same file, keyed on the model chain and the sha256 of the request JSON, looked up before the call and stored after
- [x] Test: with a counting fake model, a repeated `structured` call hits the model once
- [x] Test: a changed prompt or model id misses the cache
- [x] Test: a feedback retry misses the cache and reaches the model, so a cached bad response can't loop
- [x] Test: with a counting `fake_classifier`, a repeated `judge` hits it once, and a changed question misses
- [x] Test: with `REPLAY_CACHE` unset, no cache is installed and no file is created
