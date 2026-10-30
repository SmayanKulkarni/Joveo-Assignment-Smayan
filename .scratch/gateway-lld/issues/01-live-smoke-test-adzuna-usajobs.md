# Live smoke test: Adzuna and USAJOBS

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by:

## Question

Make real calls with the keys in root `.env` so the Gateway is designed against observed responses, not docs (the HLD research made no live call). AFK except one HITL step. About 5 Adzuna calls are approved; USAJOBS is free.

- Adzuna (country `gb` or `us`, a common role like "data engineer"):
  1. One search with `what`, `where`, `distance`, `max_days_old`. Record the full response shape, `count`, `mean`, the type of `salary_is_predicted`, `location.area`, `category.tag`, `created` format, description length.
  2. One search at a large `results_per_page` (e.g. 100) to find the real per-page cap.
  3. `GET /jobs/{country}/categories`: save the full tag list (input to Domain mapping).
  4. One `histogram` or `top_companies` call (input to [Adzuna aggregate endpoints](06-adzuna-aggregate-endpoints.md)).
  5. Spare, e.g. to see what an error body looks like.
- USAJOBS: one search with keyword + location + `Radius`, one with a multi-value param to settle the separator; record `Radius` units, `PositionRemuneration`, `ApplicationCloseDate`, `JobCategory`/family fields, `SearchResultCountAll`.
- **HITL**: the user reads the Adzuna dashboard and reports the daily and per-minute limits.

Save raw responses (no secrets) as test fixtures under `tests/fixtures/jobs/`. Throwaway script lives in the scratchpad, not the repo. Record exact shapes, latency, response headers that matter (rate-limit hints), and surprises against the research.

## Answer (2026-10-30)

Run with stdlib `urllib` from a scratchpad script, Adzuna country `us`, "data engineer" around New York / Washington DC. 5 Adzuna calls used (the cap), 6 free USAJOBS calls, all HTTP 200. Fixtures: [tests/fixtures/jobs/](../../../tests/fixtures/jobs/). Each file holds `{status, latency_ms, headers, body}` with the app id, keys and email replaced by `REDACTED`. **The dashboard quota was not reported**; it moves to [L1 cache, budget guard and replay](04-l1-cache-budget-guard-and-replay.md).

**Adzuna**
- **Page cap is 50, enforced silently.** `results_per_page=500` returned the same 50 ids as `=50`, with no error. Body: `results`, `count` (3,200), `mean`, `__CLASS__`.
- **No rate-limit headers** of any kind, so the guard can't learn the remaining quota from responses. Latency 0.8–2.5 s.
- **`redirect_url` carries our app id** as `utm_source=<app_id>`. Mapping it straight into `Posting.url` would leak the app id into state, LangSmith and the Market Brief.
- **Salary:** `salary_is_predicted` is the **string** `"1"`. In this sample, **all 50 salaries were predicted, with `salary_min == salary_max`**: Adzuna point estimates, not advertised ranges.
- `created` is ISO with `Z`. `location.area` is 4–5 levels deep, `["US", "New York", "New York City", "Manhattan", "Grand Central"]`, plus `latitude`/`longitude`. `company.display_name` was always present. No `contract_time` or `contract_type` in any of the 50 results. Descriptions run 200–500 chars. `adref` is an opaque JWT.
- **Categories (US): 30 tags.** They include non-Domain buckets: `graduate-jobs`, `part-time-jobs`, `other-general-jobs`, `unknown`. The search came back 47 `it-jobs`, 2 `scientific-qa-jobs`, 1 `engineering-jobs`.
- **`histogram`:** `{lower_bound_str: count}` in 20k bands up to an open `140000` bucket. It sums to 1,397 against `count` 3,200, so it covers only part of the matches (which part is undocumented). `where` resolved to the NYC level. **`top_companies`:** the top 5 by `canonical_name` with counts. No Posting ids in either.

**USAJOBS**
- **Responses are huge.** 25 results came to 2.0 MB, about 85 KB per item, mostly `UserArea.Details` (`MajorDuties`, `Education`, `QualificationSummary` up to 7.9 KB). At 500 per page that's about 40 MB per call.
- **Multi-location announcements.** 7 of 25 Postings list **1,176 locations**, and others list 2–44. `PositionLocationDisplay` summarises them.
- **Multi-value separator is `;`.** `2210;1550` returned 424, `2210:1550` returned 0, `2210` alone returned 385.
- **`Radius` behaves like miles:** 25 → 65 results, 100 → 74. Units aren't stated anywhere in the response. `UserArea` gives `NumberOfPages`, `IsRadialSearch` and `ResolvedLocation`.
- **There is a per-Posting remote flag**: `UserArea.Details.RemoteIndicator`, plus `TeleworkEligible`. This corrects the research, which said query-only.
- Salary: `PositionRemuneration` had one `PA` entry in all 25, with the ranges as strings. `JobGrade` (`GS`) plus `LowGrade`/`HighGrade` mark pay-table jobs. `JobCategory` usually has 1 entry, up to 11.
- Dates have no timezone and 4-digit fractions (`2027-01-31T23:59:59.9970`). Python 3.12's `fromisoformat` parses them. Id: `MatchedObjectId` (e.g. `759326100`). URL: `PositionURI`.
- Code list `occupationalseries`: 822 series, each with a `JobFamily` and an `IsDisabled` flag. No auth needed.
