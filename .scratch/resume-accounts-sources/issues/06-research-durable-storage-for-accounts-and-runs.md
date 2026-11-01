# Research: durable storage for accounts and Runs

Type: research
Status: open
Assignee: none
Blocked by: none

## Question

Where can accounts, User Profiles, resumes and Run history live so they survive a Render restart, at no cost?

- Today everything is SQLite on Render's ephemeral disk: the LangGraph checkpointer, the Store, the run registry and the gateway cache (`runtime/controller.py`, `gateway/store.py`). [What survives a restart](../../deployment/issues/04-what-survives-a-restart.md) decided that nothing is guaranteed.
- Compare free tiers: Render Postgres (does the free database still expire?), Neon, Supabase Postgres, and Turso/libSQL. For each: storage cap, connection limits, cold starts, latency to Render's region, and whether it expires or pauses.
- LangGraph support: is there a maintained async Postgres checkpointer and Store (`langgraph-checkpoint-postgres`) for the pinned LangGraph version? What does it need (psycopg 3, a connection pool, `setup()`), and does the checkpointer's write volume fit a free tier? Load `langchain-router` before reading LangGraph docs.
- Whether the gateway cache and the concurrent-resume guard (`runtime/guard.py`, a SQLite lock) can stay on local SQLite while user data moves, so the change stays small.
- Where uploaded resume files would go: in the database as text only, or in a free object store.

Capture findings in this ticket's Answer, with long notes in `../assets/`.
