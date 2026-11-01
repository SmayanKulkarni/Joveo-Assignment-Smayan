# Live Run view

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [Web API and hosting](03-web-api-and-hosting.md), [App shell and history sidebar](04-app-shell-and-history-sidebar.md)

## Question

How does a running Run read, as a chat-style stream with real-time tokens and tool-call loading states?

- The message model for the stream: what is a turn, and how `NodeStarted`, `NodeDone` notes, `Token`, `Reasoning`, `ToolCalled`/`ToolReturned` and `ApiCalled` become blocks in it.
- Token streaming: only `fetch_agent` sends `Token`s, the other LLM nodes send only `Reasoning`, and structured output is never shown as fragments. What the user sees while `clarity_check`, `plan`, `broaden` and `write_brief` draft, and how `Reasoning` shows (collapsed "thinking", dimmed) and copes with being absent.
- Tool and API loading: the card for a tool call from `ToolCalled` to `ToolReturned` (spinner, then summary and count), and a failed `ApiCalled`.
- Extraction progress as a bar from `ExtractProgress`.
- Reconnecting: the client attaches mid-Run and gets every node, tool and API line from the buffer but no earlier tokens. How the stream avoids a visible gap, and what a dropped connection shows.
- The `Stopped` and `Done` events: the failed-Run banner with Resume, the Cancel button, and the hand-off to the Brief view.
- Auto-scroll, with a "jump to latest" control when the user scrolls up.

Resolution is the block types, the reducer from event to view state, and the reconnect behaviour.

## Answer

Decided by the agent (the user delegated every decision on 2026-10-31).

**A turn is one visit to one Step**, using [Trace graph](05-trace-graph.md)'s label table. A `NodeStarted` whose Step differs from the current turn's opens a new turn. `fetch_agent` and `tools` alternating stay in one "Search job boards" turn, and a loop opens a new turn, because the stream is the chronological record and the trace is the map. The active turn is expanded. A finished turn collapses to its check, label and last note, and clicking it shows the rest. Once a Run is `done`, every turn folds under one "How this Run went" `<details>`, closed, above the Brief.

**Blocks in a turn, and the event behind each.**

| Event | Effect |
|---|---|
| `NodeStarted` | New turn if the Step changed. If the node drafts, a `drafting` line with a spinner |
| `Reasoning` | Appends to a `thinking` block: a closed `<details>` reading "Thinking…", then "Thought", body dimmed. Created on the first fragment, so no reasoning means no block |
| `Token` | Appends to a `prose` block as plain text with `white-space: pre-wrap`, and ends the drafting line. No Markdown parsing |
| `ToolCalled` | Opens a `tool` card: spinner, source name, summary |
| `ApiCalled` | Sets the source pill on the first card named `search_<source>` without one, or a turn-level pill if none: count, "cached", or red "failed" |
| `ToolReturned` | Resolves the oldest open card of that name: check, then the summary |
| `ExtractProgress` | Sets the turn's `progress` bar and "3 of 6 batches" |
| `NodeDone` | Appends its notes, and ends the drafting line |
| `Paused` | Pause card below the stream |
| `Done`, `Stopped` | See below |
| `caught_up` | Sets `animate: true`, and adds a `gap` line if needed |

- Tools pair first-in-first-out by name, since no event carries a call ID. `tools` runs calls in a `gather` but emits `tool_returned` in call order, so this is exact.
- A card still open at `Stopped` reads "Interrupted".
- **Drafting phrases:** `clarity_check` "Working out what's unclear…", `plan` "Drafting the search plan…", `broaden` "Working out how to widen the search…", `write_brief` "Drafting the brief…", `critic` "Checking claims against the numbers…". JSON fragments are never shown. Other nodes show only their label.
- `Reasoning` stays closed by default: it is a terse scratchpad (Runtime LLD §10), and the reader hands Briefs to clients.

**The reducer is one pure function** over `RunState = {turns, trace, pause, ending, connection, animate}`, and the trace's slice is the prototype's reducer in TypeScript. **Batching:** events go into a queue flushed once per frame (`requestAnimationFrame`, with a 250 ms timeout because frames stop in a hidden tab), and the reducer folds the batch. So one React render per frame carries any token rate, and a replay settles in one go. Finished turns are `memo`ised.

**Starting state.** `fromLog(detail)` groups `run_log[:live_from]` into turns by consecutive Step, and places the trace. With no live handle it reads the whole log and uses `record.status`, `pause` and `stopped_at`, so a reopened Run has its whole route and notes but no tokens or tool cards.

**Connecting, with one rule for every path.** Each stream starts from a `base` state, and `onopen` resets to `base`, because a replay starts from the current handle's start:
- First open of a new Run: empty base.
- Reload: `fromLog`.
- After answering a Pause or pressing Resume: the state on screen, with the Pause marked answered, becomes the base. This local action also takes the Step out of waiting, since the rerun Pause node's `NodeStarted` wouldn't.
- Live text sits in a separate `texts` map keyed by turn index, which `onopen` does not reset. Replays are deterministic, so indices line up, and a dropped connection keeps what was already on screen.

**Avoiding a visible gap.** Everything but tokens returns from the buffer. Text sent during the outage is lost, so `caught_up` adds one muted `gap` line, "Some live text wasn't kept", when the active turn is one that could have streamed and it was reached by replay.

**Dropped connections.** On `error` with `readyState` 0 (reconnecting), after a 2 s grace, a small "Reconnecting…" pill shows at the end of the stream. On `readyState` 2 (204 or 404), the client fetches `GET /runs/{id}` and rebuilds from it. That also covers a server restart mid-Run, which ends in the failed banner.

**Endings.** The client calls `close()` on every terminal event.
- `Paused`: the card appears from the event's own payload, and the sidebar refetches after 300 ms.
- `Done` with `done`: fetch `RunDetail`, retrying up to 5 times at 200 ms while it says `running`, then hand off to the Brief view. `aborted`: a notice with the reason, the last `run_log` message or `record.error` (the same rule as `scout show`), and a link to `/`.
- `Stopped` with a node: a banner, "Stopped at <Step>. Nothing is lost; Resume retries that step", with Resume (`answer: null`) and the raw reason in a `<details>`. If the reason is `cancelled`, it reads "You stopped this Run at <Step>". With `node: null`, nothing was checkpointed, so there is no Resume, only a link to `/`.

**Stop.** While a Run is live here, the Run header has a Stop button, with no confirmation, since Resume undoes it. A `running` Run with `live_from: null` shows "Running in another window" and polls `GET /runs/{id}` every 3 s, with no Stop.

**Auto-scroll.** The stream sticks to the bottom while a sentinel at the end is within 80 px of view (`IntersectionObserver`). Scrolling up unsticks it and shows a "Jump to latest" pill, which reads "Waiting for you" when a Pause arrived off-screen. The scroll write happens once per flush.

**Pause placement.** The card sits inline, at the end of the stream, so it is where the reader's eyes already are. The trace's waiting Step is clickable and scrolls to the card.

**Accessibility.** The stream is `role="log"` with `aria-live="off"`, since announcing every token would be unusable. A visually hidden `aria-live="polite"` region announces Step changes, Pauses and endings. Pause headings take focus on arrival when the stream is stuck to the bottom.
