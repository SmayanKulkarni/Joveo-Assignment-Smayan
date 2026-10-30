# Write docs/lld/collection.md

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01, 02, 03, 04, 05, 06, 07

## Question

Assemble the resolved tickets on this map into `docs/lld/collection.md`, in the shape of `docs/lld/request-plan.md` and including a build checklist per pass, and make the other docs agree with it. Run `langchain-router` first for the framework details: the `tools` executor, `ToolMessage`, and binding the tool through `tiers.chat`.

Known changes elsewhere:
- **Kernel:** add `fetch_results`, `relevance_verdicts`, `fetch_blocked`, `low_data_decision` and `low_data_guidance` to `State` and the owner table; `broaden` clears `fetch_results`; update §7's routing rows and §9's Caveat list.
- **Gateway:** add `calls_left(source)` to `JobsGateway` and `FakeGateway`; mark the Collection hand-ons in §17 as settled.
- **Runtime:** `"analyse"` → `analysis.fan_out(state)` in §4, the `LowDataPayload` and `LowDataAnswer` shapes in §5, and the hand-ons in §17.
- **HLD:** §3 row D, §4's diagram labels, and the attempt cap.
- **future-scope.md:** a Collection section, with at least a second tool, a cap on the Sample, and judging seniority.

## Answer

[docs/lld/collection.md](../../../docs/lld/collection.md) is written, with checklists for passes 1, 2 and 3 and a Collection section in `future-scope.md`. The HLD, Kernel, Gateway, Runtime and Request & Plan docs agree with it.

No code changed. `State`, `collection/types.py`, `JobsGateway` and `FakeGateway` keep their old shapes until step 1 of the pass 1 checklist.

Checked offline on the pinned versions: `InjectedToolArg` hides `plan` and `attempt` from the schema, a tool invoked with plain args returns its raw value, bad args raise `ValidationError`, and `FetchRecord` with `Source`-keyed dicts survives a checkpoint under strict msgpack.

Decisions made while writing, beyond the tickets:
- **`fetches: list[FetchRecord]` replaces `fetch_results: list[FetchResult]`.** A `FetchResult` can't say which Fetch it answered, and a Fetch where every source failed has none. The record carries the Fetch, the result or error, and the Attempt.
- **`broaden` doesn't clear the records.** `fetch_agent` needs to know what's been searched and `broaden` needs each title's totals, so `collect` strips their Postings instead. This reverses the ticket's "cleared by `broaden`".
- **`kernel/state.py` imports `gateway/types.py`,** which changes the Kernel and Gateway import rules.
- **`broaden` gets source totals per title,** not Relevant counts per title, because `Posting` doesn't record which title found it.
- **Closing Caveats.** Mostly federal, Old data, Broadened and Too few Postings fire once, when Collection finishes: in `relevance` when Sufficient, and in `low_data_review` on `continue`. This narrows the Caveats ticket's "at the Pause", which would repeat them for each broaden the user chose.
- **"Old" is measured from the newest `fetched_at`,** because a clock would change the Caveat text on replay and miss the LLM cache.
- **One source failed** also fires when a whole Fetch failed while another Fetch in the Attempt answered.
- **Unproven until the live smoke:** the 0.5 relevance cut, and whether 1.5× raw reaches the target in one Attempt.
