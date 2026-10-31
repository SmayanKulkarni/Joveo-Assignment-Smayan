# 01: Collection contract and the model's searches

**What to build:** given an approved Search Plan, the cheap model chooses tools, titles and pages and searches up to the cap. Each call leaves a `FetchRecord` in state and only a short summary in `messages`. This includes the prefactor the stage needs: the Gateway's per-source `fetch`, its public `calls_left`, the Collection `State` fields and the final Collection types. Spec: [Collection LLD](../../../docs/lld/collection.md) §2, §3, §5, §12, §13, §14 pass 1 steps 1-3.

The `fetch(f, source)` change is already uncommitted in the working tree (`gateway.py`, `testing.py`, `test_gateway.py`, `smoke_gateway.py`). Keep it and land it with this ticket instead of redoing it.

**Blocked by:** None (can start immediately).

**Status:** done

Contract:

- [x] `JobsGateway.fetch(f, source)` and `FakeGateway.fetch(f, source)` replace the fan-out `fetch(f)`, and the Gateway tests and smoke script use them
- [x] `JobsGateway.calls_left(source)` and `FakeGateway.calls_left(source)` are public
- [x] `State` gains `fetches`, `relevance_verdicts`, `fetch_blocked`, `low_data_decision` and `low_data_guidance`, owned by Collection, and `kernel/state.py` can import `gateway/types.py` with no import loop
- [x] `FetchRecord`, `LowDataPayload` and `LowDataAnswer` have their final fields, at the existing module path
- [x] The `low_data_review` stub, `ANSWER_FOR` and the clients still work with the larger payload, and `guidance` stays optional
- [x] `MAX_FETCHES = 6` and `MAX_BROADENS = 2` exist, and `make_nodes(deps)` and `ROUTERS` are wired into `build_graph`, overriding only the stubs of nodes that have landed
- [x] A stage imports only `runtime/deps.py` and `runtime/pause.py` from Runtime
- [x] Test: `FetchRecord`, including `FetchResult`'s `Source`-keyed dicts, and the Pause models survive the Runtime serde test

Tools and `tools`:

- [x] `search_adzuna` and `search_usajobs` each expose only `title` and `page` to the model, with `plan` and `attempt` as `InjectedToolArg`, and their docstrings state each API's real differences
- [x] `Fetch` is built from the tool's `title` and `page` plus the plan's `country`, `location`, `radius_km`, `max_days_old` and `category`, and `FetchRecord.attempt` is `len(broadened_plans)`
- [x] A US plan binds both tools and any other plan binds only `search_adzuna`, chosen from `current_plan.country` on each call
- [x] `tools` runs the calls under `asyncio.gather`, looking each tool up among those bound this Attempt, with injected values applied last
- [x] Each outcome follows §5: a good call gives a record and a summary, `GatewayError` gives a record with `error` and a `ToolMessage` with its text, an unknown tool or `ValidationError` gives `status="error"` and no record, over the cap gives a refusal and no record, and `SourceRejected` propagates
- [x] Every `ToolMessage` counts toward the cap, including refusals and bad args
- [x] The summary follows §5's format: source, title, page, Posting count and new count, then total, then at most 5 sample titles, with `calls left` only for Adzuna, and a failed call replaces the middle lines with `adzuna failed: <failure>.`
- [x] "New" means not in `postings` and not in an earlier record of this Attempt
- [x] `fetches` is written as a whole list on each update, and a Run killed mid-node reruns as L1 hits at no quota cost
- [x] Test: `plan` and `attempt` are absent from both bound schemas
- [x] Test: model args can't override `plan` or `attempt`
- [x] Test: a non-US plan binds only `search_adzuna`, and a `search_usajobs` call there is an unknown tool
- [x] Test: each tool passes its own `Source` to `gateway.fetch`
- [x] Test: `GatewayError` gives a record with `error`, bad args give an error `ToolMessage`, a 7th call is refused, and `SourceRejected` propagates
- [x] Test: no Posting text beyond sample titles reaches a message

`fetch_agent`:

- [x] Uses `tiers.chat("cheap", tools=[...], name="fetch_agent")`, and `LLMExhausted` propagates
- [x] An Attempt's first turn (`messages` empty) writes a `SystemMessage` and a `HumanMessage` holding `current_plan`, the raw goal of 1.5 × `target_postings`, the Sample so far, and already-searched `(source, title, page, total)` for records whose other Fetch fields match the current plan
- [x] Later turns send `messages` and append the reply
- [x] At `MAX_FETCHES` or more `ToolMessage`s it writes a `note` and makes no LLM call
- [x] No tool call on a first turn logs a `warning` and carries on as a normal Attempt, with no retry path
- [x] `after_fetch_agent` returns `tools` when the last message has `tool_calls`, else `collect`, including at the cap
- [x] `FETCH_SYSTEM` in `prompts.py` follows every §12 rule, with stable text first
- [x] Test with `FakeToolChatModel`: the first turn holds the plan, the already-searched list leaves out records with different Fetch settings, a turn at the cap makes no LLM call, and no tool call logs a `warning`
- [x] Test: a graph run with later stages stubbed loops `fetch_agent` → `tools` → `fetch_agent` → `collect`
- [x] The existing test suite still passes, and no test calls an LLM or a jobs API
