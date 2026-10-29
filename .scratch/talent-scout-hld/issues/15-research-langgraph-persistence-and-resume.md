# Research: LangGraph persistence and resume semantics

Type: research
Status: open
Findings: branch `research/langgraph-persistence-and-resume`, file `research/langgraph-persistence-and-resume.md`

## Question

Do current LangGraph releases support the guarantees in [How is state persisted so a Run survives the user leaving?](10-persistence-and-durable-resume.md)?

Specifically:
- SQLite checkpointer package, sync vs async variants, and its concurrency limits.
- Is there a SQLite-backed `Store` (for long-term memory), or only InMemory / Postgres? If not, what is the closest option?
- When checkpoints are written (per super-step?), durability modes, and what survives a process kill mid-node.
- Resume semantics: does the interrupted node re-run from its top? How are multiple `interrupt()` calls in one node matched on resume?
- How to discover pending interrupts and their payloads for a thread after restart (`get_state`, `tasks`, `interrupts`).
- Interaction of `interrupt()` with `Send` fan-out and with parallel branches.
- Listing threads from a checkpointer (to back a run registry), or whether a separate registry is needed.
- Current status of prebuilt `ToolNode` (location, recent breaking changes) to confirm the custom executor decision.
