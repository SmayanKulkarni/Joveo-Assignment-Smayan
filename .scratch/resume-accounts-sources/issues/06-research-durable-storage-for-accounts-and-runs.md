# Research: durable storage for accounts and Runs

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

Where can accounts, User Profiles, resumes and Run history live so they survive a Render restart, at no cost?

- Today everything is SQLite on Render's ephemeral disk: the LangGraph checkpointer, the Store, the run registry and the gateway cache (`runtime/controller.py`, `gateway/store.py`). [What survives a restart](../../deployment/issues/04-what-survives-a-restart.md) decided that nothing is guaranteed.
- Compare free tiers: Render Postgres (does the free database still expire?), Neon, Supabase Postgres, and Turso/libSQL. For each: storage cap, connection limits, cold starts, latency to Render's region, and whether it expires or pauses.
- LangGraph support: is there a maintained async Postgres checkpointer and Store (`langgraph-checkpoint-postgres`) for the pinned LangGraph version? What does it need (psycopg 3, a connection pool, `setup()`), and does the checkpointer's write volume fit a free tier? Load `langchain-router` before reading LangGraph docs.
- Whether the gateway cache and the concurrent-resume guard (`runtime/guard.py`, a SQLite lock) can stay on local SQLite while user data moves, so the change stays small.
- Where uploaded resume files would go: in the database as text only, or in a free object store.

Capture findings in this ticket's Answer, with long notes in `../assets/`.

## Answer

Researched 2026-11-02. Long notes, measurements and every source: [research-durable-storage.md](../assets/research-durable-storage.md).

### Recommendation

- **Neon Free Postgres**, one project in `aws-us-west-2` (US West, Oregon), next to Render's default Oregon region. It doesn't expire, wakes itself, and gives 1 GB.
- Move checkpoints to `AsyncPostgresSaver` and the Store to `AsyncPostgresStore` from `langgraph-checkpoint-postgres==3.2.0`. Move the run registry, accounts, User Profiles and resume text into the same database.
- Share one `psycopg_pool.AsyncConnectionPool` (small `max_size`, `check=AsyncConnectionPool.check_connection`, `autocommit=True`, `row_factory=dict_row`, `prepare_threshold=0`), because Neon drops connections when it suspends after 5 idle minutes.
- Prune finished Runs to their latest checkpoint (`aprune(..., strategy="keep_latest")`) so 1 GB lasts.
- Keep the gateway cache and budget on local SQLite. Keep the resume guard on a local file lock, but give it its own folder setting.
- Store resumes as extracted text in Postgres. No object store until a feature needs the original file.

### Key findings

- **Render Postgres Free still expires**: 30 days after creation, then a 14-day grace, then deletion. One per workspace, 1 GB, no backups ([docs](https://render.com/docs/free), read 2026-11-02; [changelog](https://render.com/changelog/free-postgresql-instances-now-expire-after-30-days-previously-90), effective 2024-05-20).
- **Neon Free**: 1 GB per project, 100 CU-hours per project per month, suspends after 5 idle minutes and can't be disabled, wakes in "a few hundred milliseconds", no expiry stated, and "None of these limits delete your data". 97 usable connections at 0.25 CU, PgBouncer in transaction mode ([plans](https://neon.com/docs/introduction/plans), [scale to zero](https://neon.com/docs/introduction/scale-to-zero), [pooling](https://neon.com/docs/connect/connection-pooling), [regions](https://neon.com/docs/introduction/regions), read 2026-11-02).
- **Supabase Free**: 500 MB database, 2 active projects, paused after 7 days of low activity and only resumed by hand (restorable for 1 year). Render can't reach Supabase's IPv6 direct host, so it has to use the shared session pooler ([pricing](https://supabase.com/pricing), [pausing](https://supabase.com/docs/guides/platform/free-project-pausing), [connecting](https://supabase.com/docs/guides/database/connecting-to-postgres), [Render guide](https://render.com/articles/how-to-connect-a-render-service-to-supabase-postgres), read 2026-11-02).
- **Turso Free**: 5 GB, 100 databases, but databases are archived after 10 days of inactivity and LangGraph has no libSQL saver or Store ([pricing](https://turso.tech/pricing), [unarchive](https://docs.turso.tech/cli/group/unarchive), read 2026-11-02).
- **`langgraph-checkpoint-postgres` fits the pins.** 3.1.3 (2026-10-12) and 3.2.0 (2026-10-14) both need `langgraph-checkpoint>=4.3.0,<5`, and we resolve 4.3.1. They add `psycopg>=3.2`, `psycopg-pool>=3.2` and `orjson`. `setup()` must run once, and needs autocommit because it uses `CREATE INDEX CONCURRENTLY`. The saver takes `serde`, so `ALLOWED_MSGPACK` carries over ([PyPI](https://pypi.org/project/langgraph-checkpoint-postgres/), 3.2.0 wheel source).
- **Write volume.** The local `runs.sqlite` holds 7 Runs in 69 MB: 0.9 to 29 MB of checkpoint history per Run, and 18 KB to 1.2 MB of final state. The Postgres saver only rewrites changed channels, and pruning finished Runs keeps about 1 MB each, so hundreds of Runs fit in 1 GB.
- **Deploy overlap.** Render keeps the old instance up until the new one starts ([deploys](https://render.com/docs/deploys)). With a shared registry, a new instance could mark a still-live Run as failed, because the file lock doesn't span machines. Either accept it, or use `pg_try_advisory_lock` on a direct connection. The LLD decides.
- **Brief files** are built from the checkpoint, so they can be rebuilt on demand and need no storage.
- **If original resume files are ever needed**: `bytea` in Postgres for a demo. Cloudflare R2's free tier is 10 GB with free egress ([pricing](https://developers.cloudflare.com/r2/pricing/), updated 2026-10-30).

### Not verified

- Neon cold-start time measured from Render, and the real latency from Render Oregon to Neon `aws-us-west-2`. Render doesn't say which AWS region its Oregon region runs in.
- The size of checkpoint history per Run on the Postgres saver. The 1 GB estimate comes from SQLite figures and the blob-per-channel-version schema.
- Whether Render's zero-downtime overlap applies to free web services.
- Whether Neon ever deletes long-idle AWS free projects. Its docs only mention deleting deprecated Azure ones.
- Whether Cloudflare R2's free tier needs a payment method on file.
- Whether `psycopg[binary]` wheels install cleanly in the project's Docker base image. Nothing was installed.
