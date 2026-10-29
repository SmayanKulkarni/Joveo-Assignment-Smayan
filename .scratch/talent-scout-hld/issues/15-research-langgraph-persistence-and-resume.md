# Research: LangGraph persistence and resume semantics

Type: research
Status: resolved
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

## Answer

Full findings on branch `research/langgraph-persistence-and-resume` (commit `7eabba5`), file `research/langgraph-persistence-and-resume.md`. Verified from package source and a cross-process experiment on langgraph 1.2.18 + langgraph-checkpoint-sqlite 3.1.2 (fresh process per step, hard kill mid-node).

- **SQLite Store exists**: `langgraph.store.sqlite.SqliteStore` (+ async) in `langgraph-checkpoint-sqlite` 3.1.2, maintained though absent from the docs index. Survived across processes in the test.
- **Checkpoint timing**: one checkpoint per super-step (parallel nodes share one). Durability modes: `async` (default; a kill right after answering a Pause rolled back to that Pause), `sync` (persisted before the next step; only the killed node re-ran), `exit` (crash lost the answer). In every mode the Pause payload is on disk before the CLI shows it.
- **Resume re-runs the paused node from its top**: confirmed. Multiple `interrupt()` calls in one node are matched by call order.
- **Finding a pending Pause after restart**: `graph.get_state(cfg)` → `.interrupts[0].value` (payload), `.tasks[0].name` (node), empty `.next` when finished. Resume with `Command(resume=answer)`; parallel interrupts take a `{interrupt_id: answer}` map.
- **Run registry still needed**: the checkpointer cannot list threads cheaply, and metadata sticks only to checkpoints of the call that set it. Cheapest: a `("runs",)` namespace in the same Store. LangGraph does not prevent two processes resuming one thread at once.
- **ToolNode**: still `langgraph.prebuilt.ToolNode` (`langgraph-prebuilt` 1.1.1), not deprecated, but churn around it (`create_react_agent` deprecated, `langchain` 1.4.7 no longer re-exports `ToolNode`). Supports the custom executor decision.
- **Untested**: two processes writing one SQLite file at once (CLI + Streamlit); skipping completed parallel siblings when one pauses (docs say yes).

Amendments to [How is state persisted so a Run survives the user leaving?](10-persistence-and-durable-resume.md) recorded there.
