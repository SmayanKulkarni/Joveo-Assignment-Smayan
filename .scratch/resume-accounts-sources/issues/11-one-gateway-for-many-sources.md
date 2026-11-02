# One gateway for many sources

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [What Arbeitnow does in the gateway](10-what-arbeitnow-does-in-the-gateway.md)

## Question

What is the smallest change that lets `JobsGateway` serve Arbeitnow beside Adzuna and USAJOBS, without building an abstraction before it's needed?

- `Fetch` checks `country` against `ADZUNA_CURRENCY`, and `fetch` hard-codes the USAJOBS rule. With three sources, where should "which countries and fields a source honours" live?
- Clients: today there's a `dict[Source, AdzunaClient | UsajobsClient]`, and each client has `search(f) -> Page`. Is a duck-typed `search` still enough, or does anything justify a `Protocol`?
- Quota: Arbeitnow has no call counter, only one lazy walk an hour ([What Arbeitnow does in the gateway](10-what-arbeitnow-does-in-the-gateway.md)). What `calls_left` returns for it, and how the walk is kept to one at a time.
- Caching: the L1 TTL for the Arbeitnow snapshot, and whether L2 (Adzuna only today) widens to it.
- `coalesce` and Duplicates across sources. Ticket 10 fixed that a missing salary never blocks a merge and the Posting with pay wins. The full ranking across three sources, and whether `merged` still reads well in the Run Notes.
- Salary mapping for each source under the Advertised and Estimated pay rule, and `region` and `domain` when a source has no place hierarchy or category.
- The Gateway LLD sections to update, and the `testing.py` fake the Arbeitnow client needs.

Load `langchain-router` if the answer reaches into tool code.

## Answer

Grilled with the user on 2026-11-02. The user accepted every recommendation.

**Amended by [Choosing among the search tools](12-choosing-among-many-search-tools.md):** `COVERAGE` holds only USAJOBS (item 1). A remote Posting has `region` `("Remote",)` (item 6) and skips the country and location filters (item 7). A failed walk is remembered for the rest of the Run (item 4).

1. **Country rules in one place.** `COVERAGE = {Source.usajobs: {"us"}, Source.arbeitnow: {"de", "gb", "fr", "ch", "nl"}}` goes in `gateway/types.py`, and a source that isn't listed (Adzuna) covers every `ADZUNA_CURRENCY` country. `fetch` raises its `ValueError` from it in place of the hard-coded USAJOBS rule, and Collection's `_bound` reads the same dict. `Fetch`'s own country validator stays.
2. **Clients.** They stay a plain `dict[Source, client]` with a duck-typed `search(f) -> Page`. No `Protocol`, because there is one caller.
3. **Quota.** Arbeitnow is left out of `Store._limits`. Each page of a walk is counted but unmetered, `calls_left` returns `None`, and a 429 is `SourceUnavailable`, as for USAJOBS today. No budget code changes.
4. **Snapshot.** The gateway is opened once per Run (`runtime/controller.py`), so the snapshot is one L1 row under a fixed key (`arbeitnow`, `"snapshot"`) with the normal L1 TTL (24 hours), not a separate 1-hour TTL, which still meets ticket 10's cap of one walk an hour. A module-level `asyncio.Lock` wraps the walk, and L1 is checked again once the lock is held, so two Runs never walk at once. Filtered Fetches go through the normal `_serve` path, so they get per-Fetch L1 rows and replay. L2 stays Adzuna-only, and an expired snapshot is never a fallback when a walk fails. A filtered L1 row can be about 2 days old. That is marked with a `ponytail:` comment, and the upgrade is a separate 1-hour TTL.
5. **Coalesce.** `_key` becomes `(not USAJOBS, salary is None, newest, key)`, and `_same_pay` treats a `None` salary as agreeing. That has two side effects. Adzuna pairs where only one has pay now merge too. And when Adzuna wins, the fuller Arbeitnow description is dropped in favour of the snippet. The "merged N Duplicates" note is unchanged.
6. **Posting mapping.** `salary`, `closes_at` and `domain` are `None`. The description has its HTML stripped with the standard library's `html.parser`, has its whitespace collapsed, and is cut at 4,000 characters, as USAJOBS does. `region` is `(Adzuna's root name for that country, city)`, where the city is the first comma-separated part of `location`, and a blank location gives the country alone. Matching Adzuna's root keeps the Brief's places chart (`brief/glance.py`) grouping by city on mixed Samples. The build ticket checks the root names against one live Adzuna response per country.
7. **Filtering a Fetch locally.** The rules are:
   - **Title:** every word of `f.title` appears among the title's words, which mirrors `title_only`.
   - **Country:** taken from the job URL's host.
   - **Location:** equals the city segment, ignoring case, which is the same rule as L2 reuse. "Munich" won't match "München". That is marked with a `ponytail:` comment, and the upgrade is an alias table.
   - **Age:** `max_days_old` is checked against `created_at`.
   - **Ignored:** `radius_km` and `category`.
   - **Paging:** pages of 50, newest first, with `total` set to the number of matches.
8. **Tests and LLD.** There is no new fake, because `FakeGateway` doesn't care which source it serves. Client tests use the existing `transport` seam with a trimmed recorded page. The Gateway LLD changes in these sections:
   - §3: `COVERAGE` and `ATTRIBUTION`
   - §4: the country check
   - §6: coalesce
   - a new §7.5 for the Arbeitnow client
   - §8: the snapshot row
   - §9: the unmetered list
   - §15 and §16: test seams and the build checklist
