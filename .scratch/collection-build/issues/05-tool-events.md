# 05: Tool events in the live view

**What to build:** a client watching a Run sees each search as it starts and what it returned, because the `tools` executor emits its own events. Spec: [Collection LLD](../../../docs/lld/collection.md) §5, §14 pass 3. [Runtime LLD](../../../docs/lld/runtime.md) §10, §16 pass 3 step 2.

**Blocked by:** 01: Collection contract and the model's searches. Also `.scratch/runtime-build` 05: Event stream, which adds `emit()` and the `ToolCalled` and `ToolReturned` mapping.

**Status:** done

- [x] The executor emits `{"type": "tool_called", "name": "search_adzuna", "summary": '"data analyst" page 1'}` when a call starts
- [x] The executor emits `{"type": "tool_returned", "name": "search_adzuna", "summary": "50 Postings, 38 new"}` when it returns, or the error text when the call failed
- [x] Test inside a one-node graph: both events are delivered for a good call and for a failed one
- [x] Test: the Controller maps them to `ToolCalled` and `ToolReturned` rather than dropping them as unknown types
