# 03: Replay, tracing and live smoke (pass 1 exit)

**What to build:** with `REPLAY_CACHE` set, jobs data replays from the same file as the LLM and Jev responses, so a recorded Run is one self-contained file. Each source call shows in LangSmith without exposing a URL or key. One live `fetch` proves the real stack works, which finishes the walking skeleton. Spec: [Gateway LLD](../../../docs/lld/gateway.md) §4 step 1, §10, §13, §16 pass 1 steps 6 and 8.

Check the `traceable` API through the `langchain-router` skill before writing the tracing. The smoke script is not in CI and spends one Adzuna call, so **get the user's OK before running it**.

**Blocked by:** 02: Budget guard and L1.

**Status:** done

- [x] The Kernel's `Replay` gains a `jobs` table with `get_jobs` and `put_jobs`, and the Gateway gets it from `open_replay`
- [x] Test: a recording Run's answer replays with `cache=replay` and the row's `fetched_at`, past its TTL and with no HTTP call
- [x] Test: a replay miss goes live, reports `miss`, and is written to the replay file as served
- [x] Test: budget counters stay in `gateway_db`, whatever the replay path
- [x] Test: with `REPLAY_CACHE` unset, no replay file is created
- [x] Each source call is a LangSmith child run `gateway:<source>`, with metadata `source`, `page`, `cache` and `calls_left`, and a summary output of count, dropped and total
- [x] Trace metadata and outputs never carry the Postings, a URL or a key
- [x] Live smoke: with the user's OK, one `fetch` returns Postings through the real stack and shows in the LangSmith project
