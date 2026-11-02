# Research: durable storage for accounts and Runs

Researched 2026-11-02 for [ticket 06](../issues/06-research-durable-storage-for-accounts-and-runs.md). All web pages were read on 2026-11-02. Most vendor pages carry no "last updated" date, so the access date is the only date for them. Free tiers change, so check these numbers again before building.

## What the app stores today

All local files, all lost on a Render restart or redeploy ([render.com/docs/free](https://render.com/docs/free): "Free web services have an ephemeral filesystem", and a free web service can't attach a disk).

| Data | Where | Code |
|---|---|---|
| LangGraph checkpoints | `runs_db` (`.cache/runs.sqlite`), `AsyncSqliteSaver` | `runtime/controller.py` `RunController.open` |
| LangGraph Store (empty today: 0 rows locally) | same file, `AsyncSqliteStore` | same |
| Run registry (`runs` table) | same file, raw `aiosqlite` | `runtime/registry.py` |
| Brief files (`brief.json`, `brief.md`) | `runs_dir/<thread_id>/` | `controller._write_brief`, served by `clients/web.py:208` |
| Concurrent-resume guard | `runs_db.parent/locks/<thread_id>.lock`, an SQLite `BEGIN IMMEDIATE` lock | `runtime/guard.py` |
| Gateway L1 cache, L2 Adzuna Postings, daily budget | `gateway_db` (`.cache/gateway.sqlite`), stdlib `sqlite3` | `gateway/store.py` |

Pinned versions (`pyproject.toml`, `uv.lock`): `langgraph==1.2.18`, `langgraph-checkpoint==4.3.1` (transitive), `langgraph-checkpoint-sqlite==3.1.2`, `aiosqlite==0.22.1`. No psycopg yet.

## Free tier comparison

Render's default region is Oregon: the Blueprint spec says "If omitted, the default value is `oregon`" for services and databases ([render.com/docs/blueprint-spec](https://render.com/docs/blueprint-spec)). `render.yaml` sets no region, so the service runs in Oregon.

| | Render Postgres Free | Neon Free | Supabase Free | Turso Free |
|---|---|---|---|---|
| Engine | Postgres | Postgres | Postgres | libSQL (SQLite fork) |
| Storage | 1 GB fixed | 1 GB per project, 20 GB per account | 500 MB DB per project (Nano), 1 GB file storage | 5 GB total |
| Expires? | **Yes. 30 days after creation, then a 14-day grace, then deleted** | No expiry stated. "None of these limits delete your data." | No expiry. **Paused after 7 days of low activity**, restorable for 1 year by clicking Resume | **Archived after 10 days of inactivity**, unarchive by CLI |
| Idle behaviour | Always on until expiry | Compute suspends after 5 min idle (can't disable), wakes "within a few hundred milliseconds" | Always on until paused, then down until a human resumes it | Scales to zero after an hour idle |
| Compute quota | 0.1 CPU, 256 MB | 100 CU-hours per project per month | Shared CPU, up to 0.5 GB RAM | 500M rows read, 10M rows written per month |
| Connections | Plan group "Max 100 connections", no pooling on free | 0.25 CU: `max_connections` 104, 97 for apps; PgBouncer transaction mode, 10,000 clients | Nano: 60 direct, 200 pooler clients | n/a (HTTP/libSQL protocol) |
| Count | One free DB per workspace | 100 projects | 2 active projects | 100 databases |
| Backups | None | Not checked | Not checked | 1-day point-in-time restore |
| Region near Render Oregon | Same platform, Oregon | `aws-us-west-2` (US West, Oregon) exists | Not checked | Not checked |
| LangGraph saver and Store | `langgraph-checkpoint-postgres` | `langgraph-checkpoint-postgres` | `langgraph-checkpoint-postgres` | **None official** |

Sources:

- Render: [render.com/docs/free](https://render.com/docs/free) ("Free Render Postgres databases expire 30 days after creation", "a grace period of 14 days", "fixed storage capacity of 1 GB", "Only one Free Render Postgres database can be active", "don't support any form of backups", "don't support managed connection pooling"). The 30-day rule dates from the changelog entry [Free PostgreSQL instances now expire after 30 days (previously 90)](https://render.com/changelog/free-postgresql-instances-now-expire-after-30-days-previously-90), effective 2024-05-20. Connection group and default plan: [render.com/docs/blueprint-spec](https://render.com/docs/blueprint-spec). **So yes, the free Render database still expires.**
- Neon: [neon.com/docs/introduction/plans](https://neon.com/docs/introduction/plans) (1 GB/project, 20 GB total, 100 CU-hours/project, 100 projects, "5 min inactivity; cannot disable"); [scale-to-zero](https://neon.com/docs/introduction/scale-to-zero) (reactivates "within a few hundred milliseconds"); [connection pooling](https://neon.com/docs/connect/connection-pooling) (0.25 CU = 104 connections, 7 reserved; `pool_mode=transaction`; use the direct host for migrations and `SET`); [regions](https://neon.com/docs/introduction/regions) (`aws-us-west-2` offers Postgres; region is fixed at project creation; only deprecated Azure free projects idle 90+ days face deletion, from 2026-10-05).
- Supabase: [supabase.com/pricing](https://supabase.com/pricing) (500 MB DB, 1 GB file storage, 5 GB egress, 50 MB max upload, 2 active projects, "paused after 1 week of inactivity"); [compute and disk](https://supabase.com/docs/guides/platform/compute-and-disk) (Nano: 60 direct, 200 pooler); [project pausing](https://supabase.com/docs/guides/platform/free-project-pausing) ("a few user requests to the database each day" avoids a pause; "restore a paused project for up to 1 year"); [connecting](https://supabase.com/docs/guides/database/connecting-to-postgres) (direct connections are IPv6 unless you buy the IPv4 add-on; on IPv4-only networks "use session mode", port 5432; the shared pooler has no prepared statements in transaction mode). Render's own guide says Render can't reach IPv6-only hosts and recommends the shared pooler: [How to connect a Render service to Supabase Postgres](https://render.com/articles/how-to-connect-a-render-service-to-supabase-postgres).
- Turso: [turso.tech/pricing](https://turso.tech/pricing) (100 DBs, 5 GB, 500M reads, 10M writes, 1-day PITR); [group unarchive](https://docs.turso.tech/cli/group/unarchive) ("Databases get archived after 10 days of inactivity for users on a free plan"); [scale to zero](https://docs.turso.tech/features/scale-to-zero) (after an hour idle).

### Reading the table

- **Render Postgres** is out. A database that is deleted 44 days after creation is the same problem as the ephemeral disk, on a slower clock. The [restart ticket](../../deployment/issues/04-what-survives-a-restart.md) already rejected it for this reason.
- **Turso** is out. LangGraph ships no libSQL checkpointer or Store, and `AsyncSqliteSaver` takes an `aiosqlite` connection, so using Turso means writing and maintaining our own saver. The 10-day archive also needs a human to unarchive.
- **Supabase** works but is the weaker choice. A week without a Run pauses the project, and only a person clicking Resume brings it back. A demo URL left for a reviewer could find its database paused. Render also has to use the shared session pooler because of IPv6. 500 MB is half of Neon's cap.
- **Neon** fits best. No expiry, no manual resume, the pause is automatic and short, the cap is 1 GB, and there is an Oregon region next to Render's default.

## LangGraph on Postgres

Package: [`langgraph-checkpoint-postgres`](https://pypi.org/project/langgraph-checkpoint-postgres/). Read from PyPI's JSON API and from the 3.2.0 wheel source on 2026-11-02.

- **Maintained and compatible.** Latest is 3.2.0 (uploaded 2026-10-14); 3.1.3 was uploaded 2026-10-12, the same day as our pinned `langgraph-checkpoint-sqlite` 3.1.2. Both 3.1.3 and 3.2.0 require `langgraph-checkpoint<5.0.0,>=4.3.0`, `psycopg>=3.2.0`, `psycopg-pool>=3.2.0` and `orjson>=3.11.5`, Python `>=3.10`. Our resolved `langgraph-checkpoint` is 4.3.1, so it fits with no LangGraph upgrade. The sqlite package has the same `langgraph-checkpoint` range.
- **Async classes.** `langgraph.checkpoint.postgres.aio.AsyncPostgresSaver` and `langgraph.store.postgres.aio.AsyncPostgresStore`. `AsyncPostgresSaver(conn, pipe=None, serde=None)` accepts an `AsyncConnection` or an `AsyncConnectionPool`, and takes `serde`, so the existing `JsonPlusSerializer(allowed_msgpack_modules=ALLOWED_MSGPACK)` carries over. The README asks for exactly that: set `LANGGRAPH_STRICT_MSGPACK=true` or pass `allowed_msgpack_modules`.
- **Connection settings.** The README requires `autocommit=True` and `row_factory=dict_row` on any connection you create yourself. `from_conn_string` also sets `prepare_threshold=0` (source, `aio.py` line 87), which disables server-side prepared statements, so it also survives a transaction-mode pooler. The Store's `from_conn_string` builds an `AsyncConnectionPool` with the same three kwargs.
- **`setup()`.** Must be called once to create tables and run migrations. It uses `CREATE INDEX CONCURRENTLY`, which can't run inside a transaction, hence `autocommit=True`, and Neon advises the direct (non-pooler) host for migrations. Tables: `checkpoint_migrations`, `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`; the Store adds `store` and `store_migrations`. pgvector is only touched if a vector index is configured, which we don't need.
- **Housekeeping.** `adelete_thread(thread_id)` and `aprune(thread_ids, strategy="keep_latest")` exist in 3.2.0. `AsyncShallowPostgresSaver` is deprecated, so pruning is the way to keep only the final state of finished Runs.
- **Scale to zero needs a pool with a check.** Neon suspends compute after 5 idle minutes and drops open connections. `from_conn_string` holds one `AsyncConnection` for the app's lifetime, so the first query after a suspend would fail. psycopg's pool docs say the pool "doesn't actively monitor its idle connections" and the fix is `check=AsyncConnectionPool.check_connection`, "Added in version 3.2" ([psycopg pool docs](https://www.psycopg.org/psycopg3/docs/advanced/pool.html)). So: one `AsyncConnectionPool(DATABASE_URL, min_size=0 or 1, max_size≈5, check=AsyncConnectionPool.check_connection, kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": 0})`, shared by the saver, the Store and the registry.

### Does the write volume fit?

Measured on a copy of the local `.cache/runs.sqlite` (69 MB, 7 Runs, 6 done), with a throwaway script in the scratchpad:

- 241 checkpoints, 19 to 51 per Run. Checkpoint plus metadata bytes total 58 MB; pending writes 13.7 MB.
- Full checkpoint history per Run: 0.9 MB to 29 MB (two large Runs at 24 MB and 29 MB).
- Final checkpoint per Run: 18 KB to 1.2 MB.

`AsyncSqliteSaver` stores every channel in every checkpoint. The Postgres saver splits channel values into `checkpoint_blobs` keyed by channel version, so a channel that didn't change isn't written again. Its history per Run will land between the final-checkpoint size and the SQLite figure. Not measured on Postgres.

Worst case at 30 MB per Run, 1 GB holds about 30 Runs. Pruning finished Runs to their latest checkpoint (`aprune([...], strategy="keep_latest")`) brings that to roughly 1 MB or less per Run, so several hundred to a thousand Runs. Time travel on finished Runs isn't used by the app, so nothing is lost. Neon says exceeding a Free limit doesn't delete data.

Compute: 100 CU-hours a month is 400 hours at 0.25 CU. The compute only runs while queries arrive. The UptimeRobot ping on `/api/meta` keeps Render awake; as long as `/api/meta` doesn't touch the database, it won't keep Neon awake. An open tab polling the Run list will, once the registry lives in Postgres. Both are fine for a demo.

Latency: Render Oregon to Neon `aws-us-west-2` is presumably in-region. Even at a cross-region 70 ms, about 40 checkpoint writes per Run add a few seconds to a multi-minute Run. A wake from suspend adds "a few hundred milliseconds" once.

## What can stay on local SQLite

- **Gateway cache and budget (`gateway_db`): stay.** It is a cache, and losing the budget counter was accepted in the restart ticket because Adzuna enforces the real quota. Moving it would add write traffic to the free tier for no durability gain. No change.
- **Concurrent-resume guard: stays, with one caveat.** The lock is per process on one machine, and the OS frees it when a process dies. That still matches Render free, which runs one instance. Two small points:
  - `take_lock` derives its folder from `runs_db.parent`. Once `runs_db` goes away, it needs its own path setting (or keep `.cache/locks`). One-line change.
  - **Deploy overlap.** Render keeps the old instance running until the new one is up, then sends SIGTERM about 60 seconds later, with a 30 s default shutdown delay ([render.com/docs/deploys](https://render.com/docs/deploys); the page doesn't say whether free services get this). Today the new instance starts with an empty disk, so it never sees the old one's Runs. With a shared registry in Postgres, the new instance's reconcile could find a `running` row whose Run is still live on the old instance, take the (local, uncontested) lock, and mark it failed. Options for the LLD: accept it (a deploy mid-Run is rare and the Run becomes resumable as `failed`), or swap the file lock for `pg_try_advisory_lock(hashtext(thread_id))` on a dedicated connection, which spans instances and is released when the connection drops, like the SQLite lock. Advisory locks are session-level, so they need the direct host, not the transaction pooler.
- **Brief files (`runs_dir`): don't need storage.** `_write_brief` builds them from the checkpoint's `State`, so the web route can rebuild them from the checkpoint on demand when the file is missing, or render them from the checkpoint directly.

## Where user data goes

- **Accounts:** a plain `users` table in the same Postgres (email unique, password hash, created_at). The uniqueness belongs in a DB constraint.
- **Run history:** the registry's `runs` table moves to Postgres with a `user_id` column. Port `Registry` from aiosqlite to psycopg: `?` placeholders become `%s`, and `ORDER BY rowid DESC` becomes `ORDER BY created_at DESC`. Checkpoints move to `AsyncPostgresSaver`.
- **Customer Profile:** the LangGraph Store is built for this ("cross-thread memory for user preferences, facts", per the `langgraph-persistence` skill). `AsyncPostgresStore` under a namespace like `("users", user_id)` with key `"profile"`, read in nodes through `runtime.store`. A plain table also works; the LLD for ticket 16 decides.
- **Resumes:** store the extracted text in Postgres (a column or a Store item under `("users", user_id)`). A resume's text is tens of KB at most, so even 1,000 users fit easily in 1 GB. Don't keep the original file unless a later feature needs it. If it does:
  - `bytea` in Postgres, capped at around 1 to 2 MB per file, is the smallest change and fits a demo's user count.
  - Cloudflare R2 free tier: 10 GB-month, 1M Class A and 10M Class B ops a month, free egress ([developers.cloudflare.com/r2/pricing](https://developers.cloudflare.com/r2/pricing/), last updated 2026-10-30). Adds an S3 client and credentials.
  - Supabase Storage: 1 GB and 50 MB per file on Free, but it shares the 7-day pause.
  - Neon lists Object Storage in some regions, not in `aws-us-west-2` ([regions](https://neon.com/docs/introduction/regions)).

## Change size, roughly

1. Add `langgraph-checkpoint-postgres==3.2.0` and `psycopg[binary]` (the README says it installs psycopg with no extras; the binary extra avoids needing libpq in the Docker image).
2. `RunController.open`: one `AsyncConnectionPool` from a new `DATABASE_URL` setting, passed to `AsyncPostgresSaver(pool, serde=...)`, `AsyncPostgresStore(pool)` and `Registry(pool)`. `setup()` on each at startup; the retry loop for racing SQLite setup can go.
3. Port `Registry` to psycopg and add `user_id`.
4. Give `take_lock` its own folder.
5. `render.yaml`: `DATABASE_URL` with `sync: false`.
6. Open for the LLD: how local dev and tests get a Postgres (a free Neon branch, or a local Docker Postgres), since keeping an SQLite path beside the Postgres one would mean two registry implementations.
