# 05: Event stream

**What to build:** the Controller turns LangGraph's stream into the full `RunEvent` set, so a client can show LLM tokens, reasoning, tool and API calls and extraction progress as they happen, and never sees a LangGraph chunk. Spec: [Runtime LLD](../../../docs/lld/runtime.md) §10, §16 pass 3 steps 1-3.

The `tools` executor's own `tool_called` and `tool_returned` emits are Collection's, and the Controller drops unknown types with a log line until they land.

**Blocked by:** 02: Run Controller and the skeleton proof.

**Status:** done

- [x] `emit()` is a no-op outside a graph and writes to the stream inside one
- [x] Test: `emit()` is delivered inside a graph and through `owned()`
- [x] The Gateway's `fetch` emits one `api_called` per source after the `gather`, with `cached` meaning a cache status other than `miss`
- [x] Test: the real Gateway on a mock transport, inside a one-node graph, emits one `api_called` per source, including a failed one
- [x] The full chunk mapping in `runtime/events.py`: `NodeStarted`, `Token`, `Reasoning`, `ToolCalled`, `ToolReturned`, `ApiCalled` and `ExtractProgress` per the §10 table
- [x] Test on a scripted graph: tokens only from `fetch_agent`, reasoning optional, and `Token` and `Reasoning` never in the replay buffer
- [x] Test: a `Send` run with one failing branch counts `ExtractProgress` correctly across the rerun, and `NodeDone` for `batch_extract` fires once

**Notes:** The Gateway's `fetch` is per source now, so it emits one `api_called` per call rather than per source after a `gather`; a raised error emits `failed=True` with `count=0`, then re-raises. `Token` and `Reasoning` are in `LIVE_ONLY` and skip the buffer. `ExtractProgress` is emitted on each `batch_extract` update, and the mapper is per stream, so the rerun counts 1 to 3 again. Not done: the `tools` executor's own emits, which are Collection's.
