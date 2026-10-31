# 01: Pause protocol, guard, registry and the stub graph

**What to build:** the foundations of Runtime. The full HLD §4 graph compiles from one wiring table with stubs for every missing stage, and a stub Run can be driven in-process to `render` through all three Pauses on an `AsyncSqliteSaver`. Pauses are typed and survive a checkpoint round trip, a per-thread lock refuses a second process, and the registry derives a Run's status from a checkpoint snapshot. Spec: [Runtime LLD](../../../docs/lld/runtime.md) §2-5, §7, §8, §15 (stubs), §16 pass 1 steps 1-5.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] `LANGGRAPH_STRICT_MSGPACK` is set in the package `__init__.py`, `rich` is added, `aiosqlite` is pinned, `runs_db` and `runs_dir` settings exist with the LLD defaults, and `runs/` is in `.gitignore`
- [x] Stage `types.py` stubs for the three payload and answer pairs sit at their final paths, and `Pause` is a discriminated union by `kind` with the `ANSWERS` table
- [x] Test: each Pause and answer survives a dump and load through the allowlisted serializer, and `model_validate` rejects a bad answer
- [x] Per-thread lock: a stdlib SQLite connection holding `BEGIN IMMEDIATE`, busy mapped to `RunLocked` by `sqlite_errorname`, held for the whole Run
- [x] Test: a second subprocess is refused, and the lock frees after a kill
- [x] `runs` table with atomic single-`UPDATE` transitions, and `derive_status` as a pure function
- [x] Test: `derive_status` for all five outcomes on a fake snapshot, and a transition updates `updated_at`
- [x] `Deps`, `stub_nodes`, `STUB_ROUTERS` and `fake_deps` exist, and `build_graph(deps, saver)` wraps every node and router in `owned()` and compiles once from the edge, conditional and owner tables
- [x] Test: the full graph compiles, and a stub Run reaches `render` with the expected three Pauses

**Notes for ticket 02:** `RunLocked` lives in `guard.py`, and `RunStatus` and `RunRecord` in `registry.py`, because the Controller imports both modules. `Registry.get` exists; `list_runs` and the conditional reconcile `UPDATE` are still to add. The `PlanReviewAnswer` cross-field validator is left to Request & Plan step 2.
