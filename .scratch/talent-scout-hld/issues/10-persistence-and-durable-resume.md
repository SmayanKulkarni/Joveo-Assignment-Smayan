# How is state persisted so a Run survives the user leaving?

Type: grilling
Status: resolved

## Question

Which persistence backs the core, and how does the system guarantee (non-negotiable) that a user can close the CLI or browser at any Pause and resume exactly where they left off?

## Answer

Resolved during charting.

**Backend**: SQLite checkpointer for threads, SQLite-backed Store for long-term preferences (Store availability to be verified, see [Research: LangGraph persistence and resume semantics](15-research-langgraph-persistence-and-resume.md)).
- MemorySaver rejected: dies with the process, fails resume-later.
- SQLite: first-party, zero infra, a file that survives restarts; evaluators can clone and run.
- Postgres: right for concurrent writers but needs a server; candidate for the infra phase.
- Redis / DynamoDB-on-MiniStack: need a server, less mature savers.
- Known ceiling: single writer. Fine for CLI; replaced in the infra phase.

**Durable resume rules** (HLD-level, non-negotiable):
1. Checkpoints are on disk after every node, including the pending Pause payload (the exact Clarifying Questions). Closing or crashing loses at most the in-flight node.
2. **Pause nodes are pure**: `clarify`, `plan_review`, `low_data_review` only call `interrupt()` and write the answer. Anything generative (e.g. drafting questions) happens in the node before, because the paused node re-runs from its top on resume.
3. Returning re-shows the same Pause: the Run Controller loads the thread, finds the pending Pause, re-displays its stored payload, resumes with `Command(resume=answer)`.
4. A **run registry** (thread, request summary, status, updated time) means users never need to remember a thread ID; CLI `--resume` lists resumable Runs, Streamlit keeps the thread ID in the URL.
5. A kill mid-node re-runs that node from the last checkpoint; repeated fetches are served from the L1 cache, costing no Adzuna quota.

**Amendments from [Research: LangGraph persistence and resume semantics](15-research-langgraph-persistence-and-resume.md)**:
- Rules 1 and 5 hold only with `durability="sync"` on every graph call (default `async` can roll a just-answered Pause back). The Run Controller always passes `sync`.
- Checkpoints are per super-step, not strictly per node; parallel `batch_extract` branches share one.
- Rule 2 tightened: exactly one `interrupt()` per Pause node, never inside `try/except`.
- Rule 4: the run registry lives in a `("runs",)` namespace of the same SQLite Store (the checkpointer cannot list threads cheaply).
- New: the Run Controller guards against two processes resuming the same thread at once, since LangGraph does not.
