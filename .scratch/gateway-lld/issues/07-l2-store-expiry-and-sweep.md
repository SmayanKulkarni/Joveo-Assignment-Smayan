# L2 store, expiry and sweep (pass 2)

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 04, 05

## Question

How does the L2 region × Domain Posting store work?

- **Schema**: Postings keyed `source:source_id`, Region and Domain columns, first-seen / last-seen, raw vs mapped.
- **Read-before-call rule**: what "enough fresh Postings for region + Domain + role" means (role matching without an LLM, count threshold, freshness), and whether it needs a target from the query (see the map's Not yet specified). `Fetch` carries no target today ([Gateway query interface](02-gateway-query-interface.md)).
- **Merge**: dedupe on key, updating changed Postings.
- **Expiry**: soft-expiry freshness window length, hard expiry from close dates, filter on read, sweep at Run start (who calls it: Runtime or the Gateway lazily).

Input from [L1 cache, budget guard and replay](04-l1-cache-budget-guard-and-replay.md): L2 can live in `gateway_db`. L1 rows now hold mapped Postings and are purged only when every Posting has closed, with a 24-hour TTL deciding refetch, and the purge runs when the Gateway opens. The user's intent of keeping Postings until they end and reusing them across queries belongs here. Decide what L2 still adds over L1, and whether the replay path (never purged, no close-date filter) must bypass it so a replayed Run stays reproducible.

Input from [USAJOBS client and mapper (pass 2)](05-usajobs-client-and-mapper.md): a multi-location USAJOBS Posting's Region is the common prefix of its locations, so a nationwide notice sits at `("US",)`, not in any city. USAJOBS Postings can carry a different Domain from the Fetch's `category`, or `None`, because the category isn't sent to that source. `PositionTitle` matches any word in the title, so stored Postings aren't all real matches for the title that fetched them.

## Answer (2026-10-30)

Grilled with the user; all recommendations accepted, except that the user rejected sweeping when the Gateway opens, which led to the sweep-on-write rule below. No API calls spent.

**What L2 is for**
- L2 skips Adzuna calls on an L1 miss, and serves as a fallback when a live call fails. It adds two savings over L1: the same search after 24 hours, and overlapping searches.
- **Adzuna only.** USAJOBS calls are free, and its Postings match poorly (nationwide notices at `("US",)`, Domains that differ from the one asked for, any-word titles). USAJOBS stays on L1 and live calls. Adzuna's `closes_at` is always `None`, so L2 needs soft expiry only, and hard expiry stays in L1. This reverses the HLD's "every Posting is stored".

**Read order** (Adzuna, per `Fetch`)
1. Replay file, when `REPLAY_CACHE` is set.
2. Fresh L1 row.
3. L2, if it can fill the requested page.
4. Guarded live call. The result is written to L1 and L2.
5. On a failed live call, L2's partial page, if it has any matches.

A replay hit returns before L2, so a replayed Run stays reproducible. During a recording Run, an L2 answer is written to the replay file like any other. L2 answers are never written to normal L1, which would restart the 24-hour TTL on old data.

**Reuse rule** (guards against a skewed Sample)
A stored Posting remembers the `Fetch` that last returned it (`via`), and is reused only if `via` was at least as broad as the new `Fetch`. Otherwise "senior data engineer" Postings would fill a later "data engineer" request and push its salary Stats up.
- **`via` must have:** the same country; every word of `via.title` in the new title; the same location, or a blank `via.location`; `via.radius_km` at least the new radius; `via.category` of `None` or the same category.
- **The Posting must have:** every word of the new title in `Posting.title` (what `title_only` would require); `posted_at` within `max_days_old`; `domain` equal to `category`, if one was given; and, if `via` was country-wide and the new location isn't blank, the new location equal to one Region segment (case-insensitive).
- **Known limits:** a wider stored radius can return a few Postings outside the new radius. A later, narrower `Fetch` overwrites `via`, which can cost an extra call but never skews the Sample.

| Stored `via` | New `Fetch` | Result |
|---|---|---|
| "data engineer", London | "senior data engineer", London | Reused, only the senior jobs |
| "senior data engineer", London | "data engineer", London | Live call |
| "data engineer", Camden | "data engineer", London | Live call |
| "data engineer", UK-wide | "data engineer", Camden | Reused, Camden jobs only |

**"Enough" means a full page**
Matches sort newest first, then by key, like `sort_by=date`. L2 serves page N only if slice `(N-1)*50 .. N*50` is full, so it never returns less than a live call would. Otherwise the call goes live, and any overlap is removed by key in `collect`. The 50 is the client's page-size constant, not a setting. `Fetch` needs no target count, which closes the map's open question without changing the interface. Only the failure fallback serves a partial page.

**Freshness**
- `l2_fresh_days` (default 7) measures time since Adzuna last returned the Posting (`last_seen_at`). Only a live call moves it, so serving from L2 doesn't extend it.
- `Fetch.max_days_old` separately limits how old the ad is, per request.
- A search can therefore go about a week without spending a call.

**Schema and merge** (in `gateway_db`)
```sql
l2_postings(key TEXT PRIMARY KEY, country TEXT, via TEXT, posting TEXT, last_seen_at TEXT)
-- plus one index on last_seen_at
```
- **Write:** every live Adzuna response, from any page, before `coalesce`, with `INSERT ... ON CONFLICT(key) DO UPDATE`. The newest version wins.
- **Read:** `WHERE country = ? AND last_seen_at >= ?`, then the reuse rule in Python, checking `via` before validating the Posting. A row that no longer validates is skipped.
- **Dropped:** Region and Domain columns, `first_seen` (nothing reads it) and raw responses (same reasoning as L1).
- **Ceiling:** about 8,750 rows (25 calls × 50 Postings × 7 days), so a scan is fine. The read gets a `ponytail:` comment naming this ceiling; the upgrade is Region and Domain columns.

**Outcome fields**
`CacheStatus` gains `store`. An L2 answer reports `cache=store`, `total` = L2's match count, `dropped=0`, `fetched_at` = the oldest `last_seen_at` served, and the current `calls_left`. A read-before-call hit spends no budget. On the failure fallback, `sources[adzuna]` is set as above and `failures[adzuna]` is also filled, so Collection's "one source failed" Caveat still fires. `GatewayError` is raised only when no source returned anything. With `store`, `total` is not Adzuna's match count, so it can't feed the sampling disclosure.

**Sweep**
- A single `_purge()` runs straight after each live write: `DELETE ... WHERE last_seen_at < cutoff` for L2, plus L1's existing delete. The tables only grow on a live write, so nothing else needs to trigger it, and cache hits and opening the Gateway do no sweep work. This reverses HLD §7's "sweep at the start of each Run".
- The read filter hides expired rows whether or not they've been deleted yet.
- The Infra shell's scheduled job can call the same method later.
- Measured on a worst-case table (8,750 rows, default SQLite durability, D: drive): sweep with nothing to delete 0.01 ms, deleting 350 rows 4 ms, read scan over 7,000 rows 23 ms checking `via` only and 39 ms validating every Posting, against 800–2,500 ms for an Adzuna call.

**New setting** (added to Kernel §13): `l2_fresh_days` (7).
