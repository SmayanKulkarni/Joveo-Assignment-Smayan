# Write docs/lld/runtime.md

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01, 02, 03, 05

## Question

Is `docs/lld/runtime.md` written, with per-pass build checklists, future-scope entries, and the Kernel's ⏳ Runtime items closed? The two `kernel/llm.py` fixes from [Research: live streaming sources](05-research-live-streaming-sources.md) are already patched, and Kernel LLD §12 is updated. The guarded `emit()` and a check that interrupts still behave with the `tasks` stream mode go on the pass 3 checklist. The simple web UI that replaces Streamlit gets a future-scope entry.

## Answer

Yes. [docs/lld/runtime.md](../../../docs/lld/runtime.md) is written, with checklists for passes 1, 2, 3 and 6, and a Runtime and Clients section in `future-scope.md`. The `kernel/llm.py` fixes and Kernel §12 were already in (commit `f600628`), and `tests/test_llm.py` passes. The Kernel's ⏳ Runtime items are closed, and HLD §3, §8 and §12 are updated.

Offline run on the pinned versions: `tasks` mode with a pause, a 3-branch `Send` with one failure, and a rerun, on `AsyncSqliteSaver` with `durability="sync"`. Interrupts and resume behave. All task starts arrive before the first `updates` chunk. On a rerun, finished branches arrive as `updates` marked `cached` with no task finish event.

Decisions made while writing, beyond the tickets:
- **Extraction progress needs no custom signal.** `total` counts task starts and `done` counts `updates` chunks, per that run. This replaces `batch_extract`'s "one done" signal from [Clients flow](03-clients-flow.md).
- **Stub payload and answer models sit in the stage `types.py`,** not `runtime/testing.py`, since checkpoints store class paths and `runtime/pause.py` imports them. Stub nodes stay in `testing.py`.
- **CLI prompts run outside `asyncio.run`,** one Controller per call, because `asyncio.run`'s SIGINT handler won't end a blocked `input()`.
- **`check_balance` is skipped when `replay_cache` is set,** so replay works without OpenRouter.
- **Small additions:** `UnknownRun`, `RunView.stopped_at`, `cancel()` returning `Stopped`, `ApiCalled.failed`, `aborted` for a Run killed before its first checkpoint, and reconcile also writing the Brief files.
- **Enum inside a Pause payload** was untested in research. The skeleton proof settles it through `ClarifyingQuestion`.
