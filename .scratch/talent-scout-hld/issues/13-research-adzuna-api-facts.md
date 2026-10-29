# Research: Adzuna API facts

Type: research
Status: open
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
