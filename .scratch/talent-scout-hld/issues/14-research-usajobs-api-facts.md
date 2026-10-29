# Research: USAJOBS API facts

Type: research
Status: open
Findings: branch `research/usajobs-api-facts`, file `research/usajobs-api-facts.md`

## Question

What does the USAJOBS Search API provide as a secondary US source, as needed by [Which jobs sources are used?](03-jobs-sources-and-tool-execution.md) and [Jobs Data Gateway caching and expiry](04-jobs-data-gateway-caching-and-expiry.md)?

Specifically:
- Auth headers (`Host`, `User-Agent` email, `Authorization-Key`) and rate limits.
- Search params: keyword, position title, location name, radius, date posted, job category / occupational series, pay grade, remote.
- Page size limits and total-count reporting.
- Posting fields: id, title, organisation, locations, `PositionRemuneration` (min/max, rate interval), `PublicationStartDate`, `ApplicationCloseDate`, qualifications / description text available.
- Job series / category codes and how they could map onto Adzuna-style Domains.
- Coverage caveat: federal-only roles; what kinds of private-sector queries return nothing.
