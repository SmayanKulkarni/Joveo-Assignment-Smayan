# 02: Run Controller and the skeleton proof

**What to build:** a caller can `start` a Run, get its typed Pause, `resume` it with a validated answer and reach `done`, with the Run surviving a hard kill and resuming from a fresh process. A failing node leaves a resumable `failed` Run. Spec: [Runtime LLD](../../../docs/lld/runtime.md) §6, §7, §9-11, §15, §16 pass 1 steps 6-7.

Pass 1 events only: `NodeDone`, `Paused`, `Done`, `Stopped`. Runtime is not done until the skeleton proof passes.

**Blocked by:** 01: Pause protocol, guard, registry and the stub graph.

**Status:** done

- [x] `RunController.open` builds the Deps, the saver (raw `AsyncSqliteSaver` with the allowlisted serde, `setup()` retried with backoff), the registry connection and the compiled graph
- [x] `start`, `resume`, `get_pause`, `get_run` and `list_runs` match the §6 API, with `check_balance` skipped when `replay_cache` is set
- [x] `RunHandle` replays the buffer then goes live, `wait()` returns the terminal event, and `cancel()` returns `Stopped`
- [x] Test: the happy path through the stub Pauses, and each refusal (`UnknownRun`, `RunLocked`, `NotResumable`, `InvalidAnswer`, `BalanceTooLow`) changes nothing
- [x] Test: a raising node gives `failed` and `Stopped`, and resume reruns only that node
- [x] Test: `cancel()` gives a resumable `failed` Run
- [x] Test: a stale `running` row reconciles on read, and a live task's row stays `running`
- [x] Test: closing a subscriber doesn't stop the Run
- [x] Test: `done` writes `brief.json` and `brief.md` with the paths on `Done`, and reconcile writes them too
- [x] Skeleton proof: a subprocess Run killed with `taskkill /F` at each Pause is resumed in a fresh process through all three Pauses to `done`, and a second process resuming a running thread gets `RunLocked`
- [x] The proof settles the `StrEnum`-in-payload question: it passed, an enum in a payload comes back typed in a fresh process, so the field stays an enum
