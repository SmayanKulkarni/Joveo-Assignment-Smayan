# Research: live streaming sources

Type: research
Status: resolved
Findings: local branch `research/live-streaming-sources` (commit `9d2b7fd`), file `research/live-streaming-sources.md`
Assignee: smayankulkarni05
Blocked by: none

## Question

What can actually be streamed to a client for a chat-assistant-style view of a Run (tokens, tool and API calls, reasoning), given the Kernel as built?

- Does `astream(stream_mode=["updates", "messages", "custom"])` deliver tokens from `Tiers.structured` and `Tiers.chat`, which call models inside their own retry and fallback loop? Does it need code changes in `kernel/llm.py`?
- Does `ChatOpenRouter` expose reasoning deltas, for which models, and in what shape?
- What do strict `json_schema` calls stream: raw JSON fragments only? What happens to already-streamed tokens on a validation retry or a fallback?
- How are tokens from parallel `Send` branches told apart?
- How can a node or the Gateway emit custom events (`get_stream_writer`), and does that work from an async node on Python 3.12 and through `owned()`?
- Do interrupts and `durability="sync"` still behave with multiple stream modes?

## Answer

The chat-style view is practical. Basis: package source, offline runs of the real `Tiers`, `owned()` and `AsyncSqliteSaver`, and about 8 live minimax calls. Provider failures were only simulated, and `deepseek/deepseek-v4.1-flash`, first in both chains, was not tested.

- **Tokens.** They arrive through `Tiers` with no wiring changes, but `messages` mode moves every LLM call onto `_astream`, so two fixes in `_CostedOpenRouter` must land first (code in the findings):
  - An `_astream` override raising `_ProviderError` on `finish_reason == "error"` (today `Tiers.chat` returns truncated text as success), on `ValueError` from the stream, and on an empty stream (both crash today with no retry or fallback).
  - `total_cost` set after the merge in an `_agenerate_with_cache` override, a private method to re-check on upgrades. Streaming otherwise loses the cost.
  - Provider-failure tests must also run under `astream`. The 60 s timeout becomes per-read (from source, untested).
- **Reasoning.** Available on minimax as `additional_kwargs.reasoning_content`, but not on every turn: a tool turn at low effort had none. Treat it as optional.
- **Structured calls.** They stream raw JSON fragments, and `parse_partial_json` handled every sampled step. Streamed tokens are never retracted. Each attempt gets a new message id, and a validation retry looks like a finished message, so structured output stays provisional until the node's `updates` chunk.
- **Parallel branches.** Told apart by `metadata["langgraph_checkpoint_ns"]`, then message id. `custom` and `updates` chunks carry no branch identity, so the writer must stamp it.
- **Custom events.** `get_stream_writer()` works from async nodes on 3.12, through `owned()`, and in `Send` branches. It raises outside a graph, so the Gateway and `Tiers` need a small guarded `emit()`.
- **Interrupts.** They work with all three modes under `durability="sync"`, arriving as an `updates` chunk. Resume re-runs the whole node, which repeats tokens and cost for any LLM call before `interrupt()`, so the pure Pause node rule matters more.

**Limits to design around:**
- Replay-cache hits give one whole message, not a typewriter effect, and identical hits may dedupe (tested with `InMemoryCache` only).
- Most calls are structured, so they show partial fields or a drafting state, not prose.
- Tokens aren't persisted, so a reloaded client has no history unless the Run Controller stores events.
- Closing the stream cancels the Run, so the graph needs its own task, apart from any client connection.
- Extraction fan-out of 50 to 200 streams should show as a progress count.
