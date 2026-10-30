# 03: State, log() and write guard

**What to build:** the graph state contract, proven on a real graph. A small test graph runs a `Send` fan-out through the guard, merges `extractions`, checkpoints to SQLite under strict msgpack, and rehydrates. A bad write from any node fails at that node with a clear `StateWriteError`, instead of blowing up later and blaming the wrong one. Spec: [Kernel LLD](../../../docs/lld/kernel.md) §4, §5, §8, §9, §10, §16 step 4.

The graph itself is test-only: graph wiring, the real checkpointer setup and the Store belong to Runtime.

Decision made when these tickets were cut, not in the LLD:
- **Stage type stubs.** `State` imports `Extraction` and `MarketBrief`, which their stage LLDs haven't defined yet. Add minimal frozen stubs at their final module paths in the Analysis and Brief packages, because checkpoints store class paths and moving a model later breaks rehydration. Those LLDs fill in the fields.

**Blocked by:** 02: Shared domain types.

**Status:** done

- [x] `State` has every field in LLD §4 with its owner, plus the `current_plan` and `sample_postings` properties
- [x] `extractions` is the only field with a reducer
- [x] `log()` appends an entry, and `LogKind` includes `caveat`
- [x] `RunLogEntry.data` accepts plain JSON only and has no timestamp
- [x] Test: each of the four guard rules raises `StateWriteError` (wrong owner, bad value type with the `ValidationError` chained, wiped `run_log`, `Send` with a non-model `arg`)
- [x] Test: a node writing `run_log` is allowed whatever its owner, and no node can write an `"input"` field
- [x] Test: mutating state in place raises, because it is frozen
- [x] Test: N parallel `Send` branches through the guard merge into `extractions`
- [x] Test: with `LANGGRAPH_STRICT_MSGPACK=true`, state round-trips through a SQLite checkpoint with no unregistered-type warnings
