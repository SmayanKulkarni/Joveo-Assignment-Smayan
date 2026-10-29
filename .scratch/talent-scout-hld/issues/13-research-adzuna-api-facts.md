# Research: Adzuna API facts

Type: research
Status: resolved
Findings: branch `research/adzuna-api-facts`, file `research/adzuna-api-facts.md`

## Question

What does the Adzuna jobs API actually provide, as needed by [Which jobs sources are used?](03-jobs-sources-and-tool-execution.md) and [Jobs Data Gateway caching and expiry](04-jobs-data-gateway-caching-and-expiry.md)?

Specifically:
- Search endpoint params: `what`, `what_or`, `where`, `distance`, `max_days_old`, `category`, `salary_*`, sort options; supported countries.
- Max `results_per_page` and practical pagination depth; does the response report a total `count`?
- Rate limits for the free tier (confirm 25/day and any per-minute limit), and how limit errors surface.
- Posting fields: id, title, company, location (`area` hierarchy, lat/long), category tag, `created` date, salary min/max, `salary_is_predicted`, contract type/time, description length (truncated?).
- Does a posting carry any expiry / closing signal?
- Category taxonomy endpoint and the list of category tags (for Domain mapping).
- Other endpoints useful for market stats (histogram, top companies, history) and whether they cost the same quota.
- Currency and salary period per country.

## Answer

Full findings on branch `research/adzuna-api-facts` (commit `39cd737`), file `research/adzuna-api-facts.md`. Sourced from Adzuna's OpenAPI spec, developer guides, legacy field docs and API Terms; no live call.

- **Paging**: no documented max for `results_per_page` or page depth; every response has `count` (total matches) and `mean` salary. The "~50 per page" in [Jobs Data Gateway caching and expiry](04-jobs-data-gateway-caching-and-expiry.md) is unconfirmed; cap at 50 until a real call settles it.
- **Rate limits**: 25/day not confirmed by any primary source. Limits are per account, shown in the Adzuna dashboard; a third-party SDK cites "25/minute, 250/day". No 429 documented (only 400/404/410/500 with `{exception, display, doc}`). Assume stats/categories calls share the quota.
- **Expiry: no signal.** Only `created` (source post date, or first-seen). Soft expiry only; pass `max_days_old` = freshness window on every search.
- **Categories**: `GET /jobs/{country}/categories` → `{tag, label}`, per country, full list not published. One call per country needed before Domain mapping (incl. USAJOBS family mapping) is final.
- **Salary**: local currency, no currency field (derive from country); period not stated; `salary_is_predicted` marks Adzuna-estimated salaries (string "0"/"1" in spec, int in examples, so accept both).
- **Location**: `location.area` hierarchy round-trips as `location0..7` params, so it works directly as the region key. Default radius 5 km, so always pass `distance`.
- **Descriptions are truncated to 500 characters.** Skills/requirements extraction works on snippets, not full ads.
- **19 countries.** Stats endpoints: histogram (semantics ambiguous), top_companies (top 5), geodata, history (1–12 months).
- **Licensing**: commercial organisations get a 14-day evaluation; aggregated use (vacancy counts, average salaries) beyond that needs written consent. Fine for the assessment demo; production use would need a licence. Terms require attribution "The Adzuna API", deletion of Adzuna data on termination, one account per entity.
