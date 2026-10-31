# 04: The real low_data_review Pause and pass 2 Caveats

**What to build:** when Collection can't get enough, the Run stops and shows the user the counts, the plans tried and any block reason. The user broadens with optional guidance, continues with what's there, or aborts, from either client. USAJOBS-related Caveats also land here. Spec: [Collection LLD](../../../docs/lld/collection.md) §3, §10, §11, §14 pass 2. [Runtime LLD](../../../docs/lld/runtime.md) §5.

LLD §14 doesn't list the client work, but the CLI and Streamlit render this Pause today and don't ask for guidance, and §10 requires it.

**Blocked by:** 03: Broadening, pass 1 Caveats and the live smoke.

**Status:** ready-for-agent

The Pause:

- [ ] `low_data_review` interrupts with a `LowDataPause` carrying `count`, `target`, `attempts`, `plans` (every plan tried, oldest first), `fetched`, `rejected`, `calls_left` and `blocked`
- [ ] It writes `low_data_decision` and `low_data_guidance`, replaced at each review, and a `pause` log entry
- [ ] `broaden` is always allowed with no cap, and is never refused for lack of quota
- [ ] `calls_left` is for information only, and nothing routes on it
- [ ] Closing Caveats are raised only on `continue`, not at each Pause
- [ ] `continue` with a Sample of zero reaches `stats`
- [ ] Test in a one-node graph with a checkpointer: the payload's fields, and each action
- [ ] Test: guidance reaches `broaden`
- [ ] Test: a further broaden past the cap returns to the Pause
- [ ] Test: closing Caveats fire only on `continue`

Clients:

- [ ] `render_pause` shows the counts, the plans tried and the block reason, shared by every client
- [ ] The CLI offers `broaden`, `continue` or `abort`, and on `broaden` asks for optional guidance, where Enter skips
- [ ] Streamlit offers the same three actions with optional guidance
- [ ] Test: both clients send `guidance` on `broaden` and leave it null when skipped

Pass 2 Caveats, each with a trigger and a non-trigger test:

- [ ] One source failed: L2 served a partial page (the record's `failures` holds its source), or a call failed while another call in the Attempt answered, written by `collect`
- [ ] Mostly federal: over 50% of the Sample is USAJOBS, as a closing Caveat
- [ ] Test: both on `FakeGateway` results with `failures` and L2 partial pages
