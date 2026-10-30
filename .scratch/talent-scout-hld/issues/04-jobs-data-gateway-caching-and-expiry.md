# How does the Jobs Data Gateway cache, budget and expire data?

Type: grilling
Status: resolved

## Question

With 25 Adzuna requests/day covering dev, samples and the live walkthrough, how does the data layer avoid wasting calls, and how does stale data leave the cache?

## Answer

Resolved during charting. A **Jobs Data Gateway** sits outside the graph, between the tools and the APIs.

- **L1, exact-query cache**: normalised request params → raw response. Makes repeat runs, tests and replay free. Short TTL of its own, since live results drift. Must-have.
- **L2, region × Domain Posting store**: every fetched Posting is stored, deduped by ID, tagged with region (from Adzuna's own location hierarchy + lat/long, no custom geohash) and Domain (from Adzuna's category tag; USAJOBS job series mapped onto the same list). Before calling the API, the Gateway checks whether L2 already holds enough fresh Postings for that region + Domain + role; if so it skips the call, otherwise it merges new results in. Built later than L1.
  - Rejected: a pure region + Domain cache as a *substitute* for role queries, because Adzuna returns at most ~50 results per page, so a broad Domain pull rarely contains enough of a specific role.
- **Expiry**: hard expiry when the source gives a close date that has passed (USAJOBS `ApplicationCloseDate`); soft expiry when the Posting is older than a freshness window (window length is LLD). Expired rows are filtered on read (never served) and purged by a sweep at the start of each Run. No background process in core; in the infra phase the sweep becomes a scheduled job.
- **Budget guard**: tracks daily Adzuna calls and refuses before the limit.
- **Replay mode**: the whole graph runs from cached responses; doubles as the test harness.
- **Update from [Research: Adzuna API facts](13-research-adzuna-api-facts.md)**: the ~50 per page limit is unconfirmed (no documented max). The L2 rationale still holds because each extra page of a broad Domain pull costs quota. Adzuna has no expiry field, so Adzuna Postings only ever soft-expire.
- **Update from [L1 cache, budget guard and replay](../../gateway-lld/issues/04-l1-cache-budget-guard-and-replay.md)**: L1 stores mapped Postings, not raw responses. A 24-hour TTL triggers a refetch, and a row is deleted only once every Posting in it has closed. Adzuna's limit is confirmed at 25 calls a day.
- **Update from [L2 store, expiry and sweep](../../gateway-lld/issues/07-l2-store-expiry-and-sweep.md)**: L2 holds Adzuna Postings only, skips a call only when it can fill the requested page, and also backs failed live calls. Soft expiry is 7 days after Adzuna last returned a Posting. The sweep runs after each live write, not at Run start.
- **Prompt caching** is a prompt-construction principle, not a component: stable instructions and schema first so batch calls share a cached prefix.
