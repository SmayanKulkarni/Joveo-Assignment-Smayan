# 01: Controller seams and the Demo Run

**What to build:** the prefactor every other ticket stands on, with no UI yet. A client can find the live handle of a running Run and know where its replay begins, and a Demo Run walks the whole graph at human speed with no `.env`, LLM or jobs API, emitting every event type a real Run does. Spec: [Web UI LLD](../../../docs/lld/web-ui.md) §3 and §4 (Demo mode), §13 pass 1 steps 1 and 2.

**Blocked by:** None (can start immediately)

**Status:** done

Scope limits, each lifted by a later ticket:
- No HTTP. FastAPI and uvicorn join the dependencies here, but nothing serves yet (02).
- `demo_brief()` must be complete enough to develop the Brief view against (05), with all recommendations, each Confidence and Caveats.

- [x] `attached(thread_id)` returns the live handle while a Run's task runs, and none once it has ended
- [x] `log_start` equals the `run_log` length at the handle's start, including after a resume
- [x] `buffered` is the buffer's length, and `brief_paths` is public with its callers updated
- [x] `graph_topology()` returns the nodes and edges from the existing tables, in `OWNERS` order
- [x] `HiringRequest`, `LogKind`, `RunLogEntry`, `ClarifyingQuestion`, `SearchPlan` and `MarketStats` are in `ALLOWED_MSGPACK`, and a load logs no "Blocked deserialization" line
- [x] With `settings.demo`, the Controller uses the demo graph and skips `check_balance`
- [x] A Demo Run emits `Token`, `Reasoning`, `ToolCalled`, `ToolReturned`, `ApiCalled` (one source cached), `ExtractProgress`, all three Pauses, a critic loop and `Done`
- [x] The demo honours plan approve, edit, reject and abort, and low-data broaden, continue and abort
- [x] A request containing "fail" stops once in `normalise_skills`, and Resume then reaches `done`
- [x] `--demo`'s settings need no `.env`, and its Runs live under `.cache/demo/`, never in real history
- [x] Demo `brief.json` and `brief.md` are written through the real `render_markdown`
- [x] All of the above run in `pytest` with `demo_delay=0`, and the existing suite still passes
