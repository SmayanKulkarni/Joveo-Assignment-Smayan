# Adzuna aggregate endpoints

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01

## Question

Handed down by HLD §10: do Adzuna's `histogram`, `top_companies` and `history` endpoints feed the Market Brief, and if so how?

- They carry no Posting IDs, so they aren't strict Evidence. Allowed as labelled context (e.g. "Adzuna-wide salary distribution"), or excluded?
- Quota cost per call against the daily budget, and which build pass (if any).
- If in: what the Gateway returns for them, and which component turns them into Stats or Insights.

Input from [Live smoke test: Adzuna and USAJOBS](01-live-smoke-test-adzuna-usajobs.md): `histogram` is `{lower_bound: count}` in 20k bands up to an open 140k bucket, and sums to 1,397 against 3,200 matches, so it covers an undocumented subset. `top_companies` is the top 5 with counts. Both resolved `where` to the city level. Each costs one quota call.

Input from [L1 cache, budget guard and replay](04-l1-cache-budget-guard-and-replay.md): the daily Adzuna limit is 25, and any aggregate call would go through the same budget guard. L1 rows hold Postings, so aggregate responses would need their own cache shape.

## Answer (2026-10-30)

Grilled with the user; both recommendations accepted. No live call spent; `history` was never called, so its real shape is unobserved.

**Excluded from every build pass:** `histogram`, `top_companies`, `history` and the search response's `mean`. The Gateway exposes only Postings and `SourceOutcome`, so no aggregate client, cache shape, `Fetch`/`FetchResult` type or budget spend is needed, and no component turns them into Stats or Insights.

- **Traceability:** none of them has Posting IDs, and the spec expects every number to trace back to real Postings.
- **`histogram`:** the New York fixture covers 1,397 of 3,200 matches (44%), an undocumented subset, and 1,059 of those (76%) sit in the open 140k+ band. It can't produce a median or middle 50%.
- **`top_companies`:** the Sample already gives top employers with Evidence, and the direct vs agency split needs per-Posting data.
- **`history`:** the spec asks for a trend in posting dates, which the Sample provides.
- **`mean`:** every salary in the smoke-test sample was predicted, so it may be an average of estimates.
- **Cost avoided:** one call per endpoint per Run would be up to 3 of the 25 daily calls, or 150 fewer Postings. Both calls made also resolved `where` to the city level, so their scope may not match the Sample's.

**`SourceOutcome.total` stays, as disclosure only.** Collection uses it for paging. It may appear in Run Notes or a Caveat, labelled as the source's own match count (for example "Analysed 50 of about 3,200 Adzuna matches"). It is never a Stat, an Insight's Evidence or a demand figure: it is an unverified keyword count that hasn't passed the relevance check. Wording and placement belong to the Collection and Brief LLDs.

**Follow-ups:** the histogram and top-companies fixtures stay as evidence for [Live smoke test: Adzuna and USAJOBS](01-live-smoke-test-adzuna-usajobs.md), and the exclusion goes in the README's known limitations (delivery task).
