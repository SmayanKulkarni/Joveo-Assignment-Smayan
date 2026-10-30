# L1 cache, budget guard and replay

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 02

## Question

How do L1, the budget guard and replay work, and how do tests fake the Gateway?

- **L1**: key (normalised query params per source), value (raw response vs mapped Postings), TTL, storage. Same SQLite file as the Kernel's replay cache (§14), the checkpointer's, or its own; sync `sqlite3` vs `aiosqlite`.
- **Hard-expiry filter on read**: L1 hits drop Postings whose close date has passed.
- **Budget guard**: per-source counters, persisted across process restarts, day boundary (UTC vs Adzuna's), limits from settings, refuse-before-limit behaviour, whether cache hits and categories calls count, what a Run sees when refused.
- **Replay** (`REPLAY_CACHE`): L1 read with TTL ignored; what a miss does (fail vs live call); the fetched-at age Collection needs for its replay Caveat.
- **Test seam** (Kernel §15's open row): fake Gateway vs fake HTTP transport fed from [Live smoke test: Adzuna and USAJOBS](01-live-smoke-test-adzuna-usajobs.md)'s fixtures.
- New settings rows for Kernel §13.

Input from [Live smoke test: Adzuna and USAJOBS](01-live-smoke-test-adzuna-usajobs.md): the user never reported the Adzuna dashboard limits, and responses carry no rate-limit headers, so the limits must come from settings. Ask the user for the dashboard numbers at the start of this ticket. USAJOBS raw responses are ~85 KB per item (2 MB for 25), which bears on storing raw vs mapped in L1.

Input from [Gateway query interface](02-gateway-query-interface.md): L1 is keyed per source from a normalised `Fetch` (it's already normalised by its validator). Fill `SourceOutcome.cache` (`hit` / `miss` / `replay`), `fetched_at` and `calls_left` (`None` = unmetered); decide what a replay miss raises. The test seam must fit `JobsGateway`'s constructor-injected clients.

Input from [Adzuna client and mapper](03-adzuna-client-and-mapper.md): every HTTP attempt sent, retries included (up to 3 per call), counts as one budget call. A `429` raises `BudgetExhausted`, so the guard should also stop spending for the rest of the day when it sees one. Credentials are query params, so the L1 key must be built from the `Fetch`, never from the request URL.

## Answer (2026-10-30)

Grilled with the user. No live call spent. The user delegated all replay decisions to the agent. The Adzuna dashboard limit is **25 calls a day**; no per-minute limit was reported.

**Storage**
- The Gateway has its own SQLite file, `gateway_db`, holding the L1 and budget tables. It uses stdlib `sqlite3` in autocommit mode, called directly from async code, like the Kernel's replay cache. A row is committed before `fetch` returns, so a kill mid-node re-serves it at no quota cost.
- MiniStack was considered at the user's request and deferred. It needs Docker, which this machine doesn't have on its PATH and evaluators would have to run, and it conflicts with [Persistence and durable resume](../../talent-scout-hld/issues/10-persistence-and-durable-resume.md)'s clone-and-run rule. Revisit in the Infra shell if required.

**L1**
- **Key:** primary key `(source, fetch.model_dump_json())`. The `Fetch` validator has already normalised it, and it contains no credentials.
- **Value:** one source's mapped Postings plus `total`, `dropped` and `fetched_at`, stored before `coalesce` runs. This reverses the HLD's raw response: the cache stays lean and nothing in it can leak the Adzuna app id.
  - A mapper fix doesn't reach rows already cached. They stay as mapped until refetched; delete `gateway_db` if the fix can't wait.
  - A row that no longer validates against `Posting` counts as a miss.
- **What's stored:** valid 2xx bodies, including empty result lists. Failures and bodies without a `results` list are not stored.
- **Refetch vs delete** are separate rules:
  - `l1_ttl_hours` (24, one setting for both sources) decides when a row stops being served and the next identical Fetch calls the API and overwrites it.
  - A row is deleted only when every Posting in it has a `closes_at` and all have passed: store `expires_at = max(closes_at)`, `NULL` if any Posting has none or the row is empty, and run `DELETE ... WHERE expires_at < today` when the Gateway opens. Adzuna rows and empty rows are never purged, only overwritten.
- **Close-date filter:** on normal hits and fresh responses, drop each Posting past its `closes_at`. These don't count in `dropped`, which is the mapper-drop Caveat input.
- A row past its TTL is not served when the budget is exhausted: that source fails with `BudgetExhausted` as usual. Serving stale data would need its own status and Caveat, and L2 is the better place for that reuse.

**Budget guard**
- Table `(source, utc_day, used)`. Both sources are counted; only Adzuna has a limit (`adzuna_daily_limit`, default 25), so USAJOBS reports `calls_left=None`. To hold calls back for a walkthrough, lower the setting in `.env`; there is no reserve setting.
- Day boundary is UTC, since Adzuna's reset time is undocumented. If it differs, a `429` catches it.
- One atomic statement runs before every HTTP attempt, retries included: `UPDATE ... SET used = used + 1 WHERE used < limit RETURNING used`. No returned row raises `BudgetExhausted`.
- Cache hits don't count. L1 is checked first, so a fresh row is still served once the budget runs out.
- **On a `429`:** set today's `used` to the limit, so the refusal survives restarts and no more calls go out until the next UTC day. Deleting the row clears it by hand.
- **What a Run sees:** the path in [Gateway query interface](02-gateway-query-interface.md). `failures[adzuna]` is filled and USAJOBS still returns for `us`; outside the US every source has failed, so `GatewayError` becomes a `ToolMessage`.

**Replay** (`REPLAY_CACHE` set)
- The replay file gets its own L1 table, in front of the normal one and next to the LLM and Jev tables, so one file is a self-contained recorded Run. Budget counters always stay in `gateway_db`, otherwise a new replay path would reset the count.
- **Read-through, like Jev (Kernel §11):** replay file, then fresh normal L1, then the guarded live call. The result is written to the replay file. A failing miss was rejected because a recording Run could then never fill the file without a second setting.
- A replay hit reports `cache=replay`, with `fetched_at` from the row. A live call during replay reports `miss`.
- The replay table stores mapped Postings too, is never purged, ignores the TTL and skips the close-date filter. Filtering would make Postings vanish as dates pass, change the prompts and miss every LLM cache entry. The age Caveat discloses the staleness.

**Test seam** (Kernel §15's open row)
- **Gateway tests:** `make_gateway(settings, transport=None)` takes an `httpx.MockTransport` serving `tests/fixtures/jobs/`, with `gateway_db` under `tmp_path`. This runs the real clients, mappers, L1 and guard.
- **Stage tests:** `FakeGateway(results)` in `gateway/testing.py` returns canned `FetchResult`s from `fetch`, matched by duck typing. No `Protocol`.

**New settings** (added to Kernel §13): `gateway_db` (`.cache/gateway.sqlite`), `adzuna_daily_limit` (25), `l1_ttl_hours` (24).

**Update from [L2 store, expiry and sweep (pass 2)](07-l2-store-expiry-and-sweep.md):** the L1 delete no longer runs when the Gateway opens. It runs after each live write, in the same `_purge()` as L2's sweep. The expired-row rule itself is unchanged.
