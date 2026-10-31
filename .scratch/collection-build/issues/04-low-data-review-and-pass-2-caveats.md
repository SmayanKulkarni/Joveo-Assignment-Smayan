# 04: The real low_data_review Pause and pass 2 Caveats

**What to build:** when Collection can't get enough, the Run stops and shows the user the counts, the plans tried and any block reason. The user broadens with optional guidance, continues with what's there, or aborts, from either client. USAJOBS-related Caveats also land here. Spec: [Collection LLD](../../../docs/lld/collection.md) §3, §10, §11, §14 pass 2. [Runtime LLD](../../../docs/lld/runtime.md) §5.

LLD §14 doesn't list the client work, but the CLI and Streamlit render this Pause today and don't ask for guidance, and §10 requires it.

**Blocked by:** 03: Broadening, pass 1 Caveats and the live smoke.

**Status:** done

The Pause:

- [x] `low_data_review` interrupts with a `LowDataPause` carrying `count`, `target`, `attempts`, `plans` (every plan tried, oldest first), `fetched`, `rejected`, `calls_left` and `blocked`
- [x] It writes `low_data_decision` and `low_data_guidance`, replaced at each review, and a `pause` log entry
- [x] `broaden` is always allowed with no cap, and is never refused for lack of quota
- [x] `calls_left` is for information only, and nothing routes on it
- [x] Closing Caveats are raised only on `continue`, not at each Pause
- [x] `continue` with a Sample of zero reaches `stats`
- [x] Test in a one-node graph with a checkpointer: the payload's fields, and each action
- [x] Test: guidance reaches `broaden`
- [x] Test: a further broaden past the cap returns to the Pause
- [x] Test: closing Caveats fire only on `continue`

Clients:

- [x] `render_pause` shows the counts, the plans tried and the block reason, shared by every client
- [x] The CLI offers `broaden`, `continue` or `abort`, and on `broaden` asks for optional guidance, where Enter skips
- [x] Streamlit offers the same three actions with optional guidance
- [x] Test: both clients send `guidance` on `broaden` and leave it null when skipped

Pass 2 Caveats, each with a trigger and a non-trigger test:

- [x] One source failed: L2 served a partial page (the record's `failures` holds its source), or a call failed while another call in the Attempt answered, written by `collect`
- [x] Mostly federal: over 50% of the Sample is USAJOBS, as a closing Caveat
- [x] Test: both on `FakeGateway` results with `failures` and L2 partial pages
