# Adzuna client and mapper

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01, 02

## Question

How does the Gateway call Adzuna and turn its JSON into Kernel Postings?

- **Params**: query fields → `what` / `what_or` / `title_only`, `where` vs `location0..n`, `distance` (always passed, default is 5 km), `max_days_old`, `results_per_page`, `sort_by`, `category`; country selection from location.
- **Mapper** (Kernel §3 duty): currency from country, `period = unknown`, `salary_is_predicted` (string or int), reversed ranges, Region from `location.area`, Domain from `category.tag`, `posted_at` from `created`, description (500-char snippet), `company` absence. What counts as a drop, and how drops are counted.
- **Transport**: timeout, retries on which statuses, how quota exhaustion surfaces (no 429 documented), attribution requirement ("The Adzuna API").

Input from [Live smoke test: Adzuna and USAJOBS](01-live-smoke-test-adzuna-usajobs.md): `redirect_url` contains `utm_source=<app_id>`, so the mapper must strip it (or build the URL another way) before it reaches `Posting.url`. `salary_is_predicted` is the string `"1"`; every salary in the sample was predicted with min == max. No `contract_time`/`contract_type` in the US sample. US categories include non-Domain buckets (`graduate-jobs`, `part-time-jobs`, `other-general-jobs`, `unknown`): decide what Domain they map to. Page cap is 50.

Input from [Gateway query interface](02-gateway-query-interface.md): map the `Fetch` fields (one `title`, `country`, `location`, `radius_km`, `max_days_old`, `category`, `page`) onto params; page size is fixed at the cap. Failures surface as `SourceUnavailable` / `BudgetExhausted`, and auth errors propagate. Fill `SourceOutcome.total` from `count`. `company` and `description` feed the Duplicate rule, so the mapper's normalisation of them matters.

## Answer (2026-10-30)

Grilled with the user; all recommendations accepted. No live call spent; checked against [tests/fixtures/jobs/](../../../tests/fixtures/jobs/).

**Params** (`GET /jobs/{country}/search/{page}`)
- `title_only=<Fetch.title>`, never `what` or `what_or`: matching the title only cuts keyword collisions per 50-result page; synonyms come from the Search Plan's title variants.
- `where=location`, `distance=radius_km` (Adzuna's unit is km). A blank `location` means country-wide: both are omitted. `location0..n` is never used.
- `sort_by=date`, so page N walks back in time inside the window; repeats from shifting pages are caught by `key`.
- Always `results_per_page=50`, `max_days_old`; `category` when set. No salary or `contract_*` filters.
- `SourceOutcome.total = count`.

**Countries**: one table of Adzuna's 19 countries → ISO currency in the Adzuna client. The `Fetch` validator rejects any other country (a planning bug, not a source failure); the table is exported so the Planning LLD can constrain the Search Plan to it.

**Mapper** (one raw result → `Posting`)
- `source_id = id`; `title`, `company` (`company.display_name`, missing → `None`) and `description` are trimmed and whitespace-collapsed, nothing more. The trailing `…` stays (`coalesce` normalises it away). No HTML stripping: none seen in 100 results; add it if it appears.
- **Salary:** both bounds missing or ≤ 0 → `None`; one bound → just that bound; reversed → swapped. `currency` from the country table, `period = unknown`, `predicted = str(v) == "1"` (accepts `"1"` and `1`). Predicted salaries are kept; Analysis decides how to treat them.
- `region = tuple(location.area)` as given (country first, e.g. `"US"`); missing → `(country.upper(),)`. `location = location.display_name`. `posted_at` = UTC date of `created`. `closes_at = None`.
- `domain = category.tag`; `graduate-jobs`, `part-time-jobs`, `other-general-jobs`, `unknown` or a missing category → `None`.
- `url`: `redirect_url` with `utm_source` and `utm_medium` removed, every other param kept (`se`/`v` may be needed by the landing page).
- **Drop** = a result whose mapping raises `KeyError`, `TypeError`, `ValueError` or `ValidationError`; counted in `SourceOutcome.dropped`, logged once with its id. No salary, a non-Domain category or no company is not a drop. A body without a `results` list → `SourceUnavailable`.

**Transport**
- `httpx`, 10 s timeout; up to 2 retries (0.5 s, 1 s) on timeout, connect error and 5xx, then `SourceUnavailable`. Every attempt sent counts as one budget call (handed to [L1 cache, budget guard and replay](04-l1-cache-budget-guard-and-replay.md)).
- `429` → `BudgetExhausted`, no retry. `401`/`403` → auth error, propagates and stops the Run (if over-quota turns out to be a 403, it fails loudly with the body logged and the guard's limit gets lowered). Any other 4xx → propagates as a bug (our params are wrong).
- `app_id`/`app_key` are query params and `httpx` logs URLs at INFO, so the `httpx` logger is set to WARNING and trace metadata never carries the URL.

**Attribution**: the Gateway exports `ATTRIBUTION[Source.adzuna]` ("The Adzuna API"); rendering it is the Brief LLD's job.
