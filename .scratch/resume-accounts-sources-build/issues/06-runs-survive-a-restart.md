# 06: Runs survive a restart

**What to build:** With `database_url` set, a Run started before a restart can still be opened and resumed after it. With it unset, everything works on local SQLite as today. [Research: durable storage](../../resume-accounts-sources/issues/06-research-durable-storage-for-accounts-and-runs.md) is the spec.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `langgraph-checkpoint-postgres` 3.2.0 is pinned, and checkpoints use `AsyncPostgresSaver` with `ALLOWED_MSGPACK` carried over
- [x] One shared connection pool with `check_connection`, `autocommit`, `dict_row` and `prepare_threshold=0` survives Neon suspending
- [x] The run registry moves to the same database, created by idempotent startup SQL beside `setup()`, with a `ponytail:` comment naming the no-Alembic ceiling
- [x] Table SQL is plain and uses only TEXT-style columns, so one set of statements serves both databases, with `?` swapped for `%s` on Postgres
- [x] Finished Runs are pruned to their latest checkpoint
- [x] The gateway cache and budget stay on local SQLite, and the resume guard stays a local file lock in its own folder setting
- [x] The service refuses to start on Render with `database_url` unset, and anywhere with both `database_url` and `replay_cache` set
- [x] `seed_runs` runs only in local mode
- [x] A test covers start, restart and resume against a real Postgres when one is configured, and is skipped otherwise; local-mode tests still pass
