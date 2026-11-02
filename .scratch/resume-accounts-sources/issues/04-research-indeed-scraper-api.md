# Research: Indeed Scraper API on RapidAPI

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

What does the Indeed Scraper API (border-line, on RapidAPI: <https://rapidapi.com/border-line-border-line-default/api/indeed-scraper-api>) offer, and can its "create a task and wait for results" model fit a Collection tool call?

- The task model: create task, poll or wait, fetch results. Typical and worst-case time to results, and whether a synchronous "wait" endpoint holds the HTTP call open (and for how long).
- Parameters (query, location, country or Indeed domain, radius, date posted, job type, page or max results) and how they map onto `Fetch`.
- Field mapping to `Posting`, including salary (Indeed's own estimate or Advertised) and a stable `source_id`.
- Quota, price and how a task is counted. Error and timeout behaviour.
- Terms: it scrapes a site whose terms forbid scraping. Record what the listing says, so [What Arbeitnow does in the gateway](10-what-arbeitnow-does-in-the-gateway.md) can weigh it.

Docs and playground are enough. A live call needs the key from [Subscribe to the job APIs and add keys](09-subscribe-to-the-job-apis.md). Capture findings in this ticket's Answer, with long notes in `../assets/`.

## Answer

Researched 2026-11-02. Docs only, with no key and no live call. Long notes, with full tables, are in [research-indeed-scraper.md](../assets/research-indeed-scraper.md).

### Recommendation

- It can fit a Collection tool call, but not through today's `get_json`. The API needs a POST. That POST must not be retried, because each retry queues a new scrape and spends a request. The client also needs a poll fallback on `GET /api/job/{id}` and a per-source timeout well above the current 10 s (about 60 s total).
- Make one call per (title, place) with `maxRows` set to the plan's row cap. Billing is per request, not per row, and there is no page parameter.
- Send every filter explicitly (`location`, `radius`, `fromDays`, `jobType`, `level`, `remote`). The documented defaults apply filters, and the spec and README disagree on what those defaults are.
- The free tier (25 requests a month) is enough for a smoke test only. A real trial needs PRO ($24.99, 4,000 requests a month, 5 a minute).
- For ticket 10, weigh the terms risk as high. Indeed's Site Rules forbid scrapers outright, and the listing has no terms of its own.

### Key findings

All of these come from the [listing](https://rapidapi.com/border-line-border-line-default/api/indeed-scraper-api) unless marked otherwise. WebFetch renders only the page title, but the page HTML embeds the README, the OpenAPI spec and the billing plans.

- **Task model**: `POST /api/job` ("Create a new task and wait for results") "Queues a new job ... Waits for the scraper results data or returns jobId if it take too much time." `GET /api/job/{id}` returns the same job object (`state`, `progress`, `returnvalue.data[]`). `state` is one of `active`, `waiting`, `delayed`, `prioritized`, `waiting-children`, `completed`, `failed`. An optional webhook is available.
- **Timing**: nothing says how long the POST waits before it returns an id, or what the worst-case time is. RapidAPI's measured scores are a mean latency of 6,293 ms, a 94% success rate and a 99% service level.
- **Parameters**: `query` is the only required field. The rest:
  - `location`
  - `maxRows`
  - `country`: 55 codes, with `uk` for Britain
  - `radius`: 5, 10, 15, 25, 50 or 100 miles
  - `fromDays`: 1, 3, 7 or 14
  - `jobType`
  - `level`: entry, mid or senior
  - `remote`: only `remote` or `hybrid`
  - `sort`: relevance or date

  There is no page parameter and no category. In `Fetch` terms, radius_km and max_days_old snap up to the nearest allowed value, and anything over 14 days is capped. All 19 Adzuna countries are covered.
- **Posting mapping**:
  - `jobKey` becomes `source_id`. This is Indeed's `jk`, but the doc examples don't match the `jk` in `jobUrl`, so check it live.
  - `title`, `companyName` and `location.formattedAddressShort` map directly. `datePublished` gives the date. `descriptionText` becomes the description, and `jobUrl` becomes the url.
  - There is no closing date and no domain.
- **Salary**:
  - The fields are `salaryMin`/`salaryMax`/`salaryCurrency`/`salaryType`/`salaryText`.
  - `salarySource` is `EXTRACTION` or `USER_PROVIDED`. Both are advertised pay, not an Indeed estimate, so set `predicted=False`.
  - The `salaryType` casing is inconsistent (`YEARLY`, `HOURLY`, `hourly`). The currency enum lists only USD, EUR and GBP.
- **Quota and price**: "A call to any endpoint is one request", so polls count too.

  | Plan | Price / month | Requests / month | Rate limit | Rows per call | Overage |
  |---|---|---|---|---|---|
  | BASIC | free | 25 (hard cap) | none listed | 50 | none |
  | PRO | $24.99 | 4,000 | 5 / min | 50 | $0.05 |
  | ULTRA | $49.99 | 10,000 | 8 / min | 75 | $0.045 |
  | MEGA | $129.99 | 30,000 | 15 / min | 100 | $0.04 |

  The listing offers up to 1,250 rows per call on request.
- **Errors**: `BaseErrorDto {message, error, statusCode}` for 3XX, 4XX and 5XX. A failed scrape comes back as `state: "failed"`. `GET /health` returns 503 when the service is down. Under our gateway, a non-429 4xx becomes `SourceRejected` and stops the Run.
- **Terms**:
  - The listing's `termsOfService` is null, and no plan has a legal document. The README never mentions Indeed's terms. The description advertises "avoid blocking".
  - The [RapidAPI Terms](https://rapidapi.com/terms/) put the duty on the provider, who warrants that "it owns (or has full rights to)" what it lists.
  - The [Indeed Terms](https://www.indeed.com/legal), Section D item 21, ban "any automated system (bots, scrapers, spiders, AI or Agentic AI) to access, data-mine, or submit content to the Site" without written permission. They also say "You may not crawl, scrape, extract data from" the Site.
- **Provider**: team "borderline", 1,200 subscribers, created 2024-12-25, last updated 2025-08-05. It is self-hosted on a bare-IP sslip.io host. No Apify actor or vendor docs sit behind it.

### Not verified

- How long the POST waits before it returns a task id, and the typical and worst-case scrape times.
- Whether leaving out `jobType`, `level`, `remote` or `location` means no filter or the default value, and how to search country-wide.
- Whether `jobKey` equals the `jk` in `jobUrl` and stays stable across scrapes.
- Which `salaryType` and `salaryCurrency` values come back outside the US, UK and EU, and whether Indeed's own salary estimates ever appear.
- The status codes for rate-limit and quota errors (RapidAPI usually returns 429). Whether a failed scrape or a POST that times out still counts as a request.
- That the backend is BullMQ. This is an inference from the response shape.

## Out of scope

On 2026-11-02 the user dropped every RapidAPI source and kept only Arbeitnow. This research stays as a record and feeds no decision.
