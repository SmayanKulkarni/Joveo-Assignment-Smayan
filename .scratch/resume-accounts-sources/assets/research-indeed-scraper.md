# Research notes: Indeed Scraper API (borderline, RapidAPI)

Researched 2026-11-02. Docs only, no API key, no live call.

## Sources

- **Listing**: <https://rapidapi.com/border-line-border-line-default/api/indeed-scraper-api>. WebFetch gets only the title, but the HTML from a plain `curl` carries the Next.js data with the README, the OpenAPI 3.0 spec, the endpoint list, the billing plans and the listing scores. Every claim below marked "listing" comes from that data, as served on 2026-11-02.
- **OpenAPI spec** (inside the listing): `info.title` is "INDED", version 1.0. It has three paths: `POST /api/job`, `GET /api/job/{id}` and `GET /health`.
- **RapidAPI Terms of Service**: <https://rapidapi.com/terms/>, which the listing footer links to. The listing says it was updated on May 25, 2026.
- **Indeed Terms of Service**: <https://www.indeed.com/legal>, last updated September 29, 2026.

No Apify actor or vendor docs sit behind this listing. The listing's `websiteUrl` is `http://tw00o8owgs44g8ggko8skscc.51.75.241.63.sslip.io/openapi`, a bare-IP sslip.io host, which means a self-hosted server. I did not open it. The Apify "Indeed Scraper" actors that search turns up (mlg14, scrapapi, runtime) belong to other vendors. A dev.to post quoting "500 free requests, $9.99 / $29.99 / $79.99" describes a different RapidAPI listing, not this one.

## Provider and listing facts (listing)

| Field | Value |
|---|---|
| Owner | Team "borderline" (`border-line-border-line-default`) |
| Host | `indeed-scraper-api.p.rapidapi.com` |
| Category | Jobs, FREEMIUM |
| Created / last updated | 2024-12-25 / 2025-08-05 |
| Subscribers | 1,200 |
| Scores | avgLatency 6,293 ms, avgSuccessRate 94%, avgServiceLevel 99%, popularity 9.7 |
| `termsOfService` | `null` |
| Plan `legalDocumentId` | empty on every plan |

## Task model

The endpoint names come from the listing's endpoint list. The descriptions come from the OpenAPI spec.

| Endpoint | Playground name | Spec description |
|---|---|---|
| `POST /api/job` (`addJobAndWait`) | "Create a new task and wait for results" | "Queues a new job with the given input parameters. Waits for the scraper results data or returns jobId if it take too much time." |
| `GET /api/job/{id}` (`getJob`) | "Retrieve job results by task ID" | "Fetches the job details and status by the provided unique job ID. If the job has completed, returns final results." |

- The POST holds the HTTP call open until the scrape finishes or until an undocumented server-side wait expires. After that it returns the task id, and you poll the GET.
- Both endpoints return the same `ApiResponseDto`: `id`, `name`, `data` (the input echoed back), `state`, `progress`, `returnvalue` (`{data: ScraperJobResultDto[]}`), `attemptsStarted`, `attemptsMade`, `timestamp`, `processedOn` and `finishedOn`. `state` is one of `active`, `delayed`, `prioritized`, `waiting`, `waiting-children`, `completed`, `failed`.
- That field set and state enum match a BullMQ job object exactly, so the backend is probably a NestJS and BullMQ queue. This is my inference, not something the listing says.
- Webhook: an optional `webhook: {url, headers[{key, value}]}` beside `scraper`. The README says the scraper "can POST results to your specified URL upon completion". We have no public URL, so it doesn't help us.
- **Time to results**: the only number published anywhere is RapidAPI's measured mean latency of 6,293 ms. Nothing documents a typical scrape time, a worst case, or how long the POST waits before it returns a task id.

## Parameters

Request body: `{"scraper": ScraperInputDto, "webhook"?: WebhookInputDto}`. Only `query` is required.

| Field | Type / allowed values (spec) | Spec default | README default |
|---|---|---|---|
| `query` | string | "Developer" | none (required) |
| `location` | string | "San Francisco" | "Paris" |
| `maxRows` | number | 15 | 20 |
| `jobType` | `fulltime`, `parttime`, `contract`, `internship`, `temporary`, `commission` | fulltime | fulltime |
| `level` | `entry_level`, `mid_level`, `senior_level` | senior_level | entry_level |
| `radius` | string enum `5`,`10`,`15`,`25`,`50`,`100` (README: miles) | "50" | "5" |
| `sort` | `relevance`, `date` | relevance | relevance |
| `fromDays` | string enum `1`,`3`,`7`,`14` | "14" | "1" |
| `remote` | `remote`, `hybrid` | remote | remote |
| `country` | 55 codes, `uk` for Britain (README maps each to `xx.indeed.com`, `us` to `www.indeed.com`) | us | us |

- There is no page or offset parameter. The README says "The scraper automatically handles multi-page results, but keep an eye on `maxRows`." `scrapingInfo.page` in each row records the Indeed page it came from.
- The docs don't say whether leaving out `jobType`, `level` or `remote` means "no filter" or "apply the default". Both default tables apply a filter, and the two tables disagree. `remote` has no "any" or "onsite" value. Until a live call settles it, send every field explicitly.

### Mapping onto `Fetch`

| `Fetch` field | Indeed field | Note |
|---|---|---|
| `title` | `query` | direct |
| `country` | `country` | `gb` becomes `uk`. All 19 `ADZUNA_CURRENCY` countries are in Indeed's list. |
| `location` | `location` | Country-wide (blank) is undocumented. Blank may fall back to the default city. |
| `radius_km` | `radius` | km / 1.609, snapped up to the next allowed value. 100 mi is about 161 km, which covers the plan's 100 km cap. |
| `max_days_old` | `fromDays` | Snap up to 1/3/7/14. The plan allows up to 60, so anything over 14 gets capped and narrows the search. |
| `category` | none | no category filter |
| `page` | none | Make one call per (title, place) with `maxRows` set to the plan's row cap. Every row comes from one call. |
| (seniority, employment type, work mode) | `level`, `jobType`, `remote` | These match `HiringRequest` fields `Fetch` doesn't carry today. `remote` can't express onsite or any. |

## Field mapping to `Posting`

From `ScraperJobResultDto` in the spec. Only `title` is marked required.

| `Posting` | Indeed | Note |
|---|---|---|
| `source` | new `Source.indeed` | |
| `source_id` | `jobKey` | Indeed's `jk` key, so it is stable across scrapes if it equals the `jk` in `jobUrl`. In both the spec and README examples, `jobKey` does not match `jk` in `jobUrl` (spec: `298800e819c1f9d0` vs `4cc558d3d1e9d332`). Check this live. The fallback is to parse `jk` from `jobUrl`. |
| `title` | `title` | |
| `company` | `companyName` | |
| `location` | `location.formattedAddressShort` | e.g. "Dallas, TX" |
| `region` | from `location.countryCode`, `location.city` | No state field in the spec. The README shows `formattedAddressLong`. |
| `domain` | `None` | `occupation[]` exists but doesn't match `ADZUNA_CATEGORIES` |
| `posted_at` | `datePublished` | The spec shows an ISO datetime, the README shows `"2025-02-24"`. Take the date part. `age` ("Just posted") is the fallback. |
| `closes_at` | `None` | `expired` is a boolean only |
| `description` | `descriptionText` | `descriptionHtml` is also returned |
| `url` | `jobUrl` | `applyUrl` is the employer link |
| `salary` | `salary` (`SalaryInfoModel`) | see below |

### Salary

- `SalaryInfoModel`: `salaryMin`, `salaryMax`, `salaryCurrency`, `salaryType`, `salarySource`, `salaryText`, plus Indeed UI fields (`featureTokens`, `matchingSalary`, `salaryLabel`, ...).
- `salarySource` enum: `EXTRACTION` or `USER_PROVIDED`. Neither value marks an Indeed salary estimate. EXTRACTION reads as pay parsed from the ad text, and USER_PROVIDED reads as employer-entered pay. Both are advertised pay, so set `predicted=False`. The docs don't say whether Indeed's own estimated ranges ever come through.
- `salaryType`: the spec enum is `DAILY`, `MONTHLY`, `YEARLY`, but the spec example is `HOURLY` and the README uses lowercase `hourly`. Map case-insensitively onto `PayPeriod` (YEARLY to annual) and fall back to `unknown`.
- `salaryCurrency`: the spec enum lists only `USD`, `EUR`, `GBP`. It is unknown what comes back for INR, CAD, AUD and so on. If the value fails `CurrencyCode`, drop the salary rather than the posting.
- The README example is internally inconsistent: `salaryText` "$20 - $22 an hour" next to `salaryMin` 250 and `salaryMax` 350. The spec example says 20 and 22. Validate min and max against the text before trusting them.

## Quota and pricing (listing billing plans)

The billing item is "Requests", described as "A call to any endpoint is one request." Every POST and every polling GET counts as one request, whatever the row count.

| Plan | Price / month | Requests / month | Limit type | Overage / request | Rate limit | Max rows per call |
|---|---|---|---|---|---|---|
| BASIC | $0 | 25 | hard | none | none listed | 50 |
| PRO | $24.99 | 4,000 | soft | $0.05 | 5 / minute | 50 |
| ULTRA | $49.99 | 10,000 | soft | $0.045 | 8 / minute | 75 |
| MEGA | $129.99 | 30,000 | soft | $0.04 | 15 / minute | 100 |

- Each plan has the feature note "Need more? Contact us to unlock higher limits per request (up to 1250 rows per call)". There is also one private custom plan ($89, 20,000 requests).
- BASIC's 25 requests a month cover a smoke test, not a Run.
- At PRO's 5 requests a minute, a Run that fans out more than 5 Indeed calls queues behind the rate limit.
- Cost per row at full calls: PRO is about $0.000125 per row (4,000 x 50 rows for $24.99).

## Errors and timeouts

- In the spec, every endpoint returns `BaseErrorDto {message, error?, statusCode}` for 3XX, 4XX and 5XX.
- A scrape that fails shows up as `state: "failed"` inside an HTTP 200 job object. `attemptsMade` shows the retries.
- `GET /health` returns 503 with `{status: "error", ...}` when the service is unhealthy.
- Under "Common Errors", the README lists only: a missing `query`, invalid enum values, and a wrong `x-rapidapi-key`.
- The docs don't cover rate-limit or quota responses. RapidAPI's gateway normally answers 429 for both, but I didn't check RapidAPI's docs for this.
- Fit with our gateway (`src/talent_scout/gateway/http.py`):
  - `TIMEOUT = 10` s sits just above the 6.3 s mean, so slow scrapes will time out.
  - `get_json` is GET-only, but this API needs a POST.
  - `get_json` retries a transport timeout up to twice, and each retry would queue a new scrape and spend another request. An Indeed client must not retry the POST. On a timeout or a returned id it should poll the GET instead, with a longer per-source timeout (say 60 s total).
  - Any 4xx other than 429 becomes `SourceRejected`, which stops the Run. That is right for a bad enum value. A 403 for an unsubscribed or over-quota key would also stop the Run.

## Terms

- **The listing**:
  - `termsOfService` is `null`, and no billing plan has a legal document attached.
  - The README never mentions Indeed's terms, robots.txt, permission or lawful use.
  - The description sells the product with "avoid blocking" and suggests uses like "benchmark salaries".
- **RapidAPI Terms**: "API Provider represents and warrants that ... it owns (or has full rights to) to market, promote, offer to sell, sell, grants access to, and distribute the APIs it lists via the Service and all API Content/Terms posted to the Service." Responsibility for the right to resell the data sits with the provider. That puts no obligation on Indeed, and it doesn't protect us.
- **Indeed Terms**, Section D, item 21 (Site Rules), prohibits users from:
  - "Use any automated system (bots, scrapers, spiders, AI or Agentic AI) to access, data-mine, or submit content to the Site" "without Indeed's express written permission (we conditionally grant permission to crawl the Site solely as outlined in our robots.txt file)".
  - "Access the Site through any means other than the public interfaces provided by Indeed".
  - "Bypass any security measures or Site limitations".
  - It also says "You may not crawl, scrape, extract data from, reproduce, duplicate, copy, ..." the Site.
  - It bars access "for the development, training, fine-tuning, or improvement of any third-party machine learning model".
- Using this API means we consume data the vendor got in breach of Indeed's terms. The vendor carries the direct breach. Our exposure is commercial and reputational, and the API could disappear if Indeed blocks it.
