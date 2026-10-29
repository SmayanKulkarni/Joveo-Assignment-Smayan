# Research: USAJOBS API facts

Type: research
Status: resolved
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

## Answer

Full findings on branch `research/usajobs-api-facts` (commit `b387f01`), file `research/usajobs-api-facts.md`. Response shape is from docs, not a live call; confirm on first real call.

- **Auth**: `Host: data.usajobs.gov`, `User-Agent: <registered email>`, `Authorization-Key: <key>` on `GET https://data.usajobs.gov/api/Search`. Code-list endpoints need no auth.
- **Limits**: no published per-second/per-day quota; 10,000 rows per query, 500 per page. OPM may add quotas without notice, so the Gateway budget guard should still count calls.
- **Paging**: `ResultsPerPage` up to 500; totals in `SearchResultCountAll` and `UserArea.NumberOfPages`. One call usually covers a role + location.
- **Salary**: `PositionRemuneration[]` with `MinimumRange`/`MaximumRange` (strings) and `RateIntervalCode` (PA, PH, PD, BW, PM, ...).
- **Expiry**: `ApplicationCloseDate` and `PublicationStartDate` (ISO 8601 UTC) present, so the hard-expiry rule holds. Dedupe key: `MatchedObjectId`.
- **Remote**: query filter only (`RemoteIndicator`), no per-posting flag.
- **Domains**: 822 occupational series, each with a `JobFamily` parent (60 groups); draft family→Adzuna category mapping in the findings, Adzuna tags still to be cross-checked against [Research: Adzuna API facts](13-research-adzuna-api-facts.md).
- **Coverage**: federal-only (some overseas, filter by `CountryCode`); private-sector titles likely return little. Federal pay comes from fixed pay tables, so it is not a market signal and must not be mixed unlabelled into Adzuna salary stats.
- **Unconfirmed**: `Radius` units; multi-value separator (semicolon vs colon in docs).
