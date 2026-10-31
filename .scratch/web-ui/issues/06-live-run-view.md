# Live Run view

Type: grilling
Status: open
Assignee: none
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
