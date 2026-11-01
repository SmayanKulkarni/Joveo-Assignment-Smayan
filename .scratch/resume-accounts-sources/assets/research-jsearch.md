# JSearch research notes

Researched 2026-11-02, from docs only. There was no key, so no live call.

## Sources

- [S1] Vendor LLM doc for JSearch, last updated 2026-05-27: <https://www.openwebninja.com/api/jsearch/llms.txt>
- [S2] Vendor OpenAPI spec: <https://openwebninja.s3.us-east-1.amazonaws.com/portal/openapi/jsearch.yaml>
- [S3] Vendor product page, which has the pricing table, FAQ and sample responses: <https://www.openwebninja.com/api/jsearch>
- [S4] RapidAPI listing: <https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch>. WebFetch shows only the title, so I fetched the raw HTML with curl and read the provider readme, endpoint list, billing plans and score from the page's embedded JSON.
- [S5] OpenWeb Ninja Terms of Service, last updated Oct 14, 2026: <https://www.openwebninja.com/terms>
- [S6] RapidAPI response headers doc, linked from the JSearch readme: <https://docs.rapidapi.com/docs/response-headers>. I did not fetch it.

The vendor portal pricing page (`app.openwebninja.com/api/jsearch/pricing`) returns 401 without a login.

## Two ways in

| | RapidAPI | OpenWeb Ninja direct |
|---|---|---|
| Base URL | `https://jsearch.p.rapidapi.com` | `https://api.openwebninja.com/jsearch` |
| Auth | `X-RapidAPI-Key: <key>` and `X-RapidAPI-Host: jsearch.p.rapidapi.com` [S4] | `x-api-key: <key>` [S1][S2] |
| Plans | BASIC, PRO, ULTRA, MEGA [S4] | Same tiers plus Pay As You Go [S3] |

The vendor FAQ says: "Both routes serve identical endpoints, parameters, and response shapes; the direct portal route avoids RapidAPI's data transfer limits." [S3]

## Endpoints

RapidAPI lists exactly four routes: `/search-v2`, `/job-details`, `/estimated-salary` and `/company-job-salary` [S4]. The old `/search` endpoint with a `page` parameter is described in the RapidAPI readme prose, but it is not in the endpoint list. The vendor FAQ calls `/search-v2` with `cursor` "the recommended path" for anything past page one [S3].

### GET /search-v2 (Job Search) [S1][S2]

| Param | Notes |
|---|---|
| `query` (required) | Free text. Put the title and location in it, e.g. `developer jobs in chicago`. Adding `via linkedin` filters by publisher [S3]. |
| `cursor` | Opaque. Pass `data.cursor` from the previous response. It is null when there are no more pages. |
| `num_pages` | 1 to 20, default 1. Each page holds up to 10 jobs and costs 1 request credit. |
| `country` | ISO 3166-1 alpha-2, default `us`. You must set it for jobs outside the US. |
| `language` | ISO 639. Defaults to the country's primary language. |
| `date_posted` | `all`, `today`, `3days`, `week` or `month`. Default `all`. |
| `work_from_home` | Boolean, remote jobs only. |
| `employment_types` | Comma list of `FULLTIME`, `CONTRACTOR`, `PARTTIME`, `INTERN`. |
| `job_requirements` | `under_3_years_experience`, `more_than_3_years_experience`, `no_experience`, `no_degree`. |
| `radius` | Kilometres. Sent to Google as `lrad`. The docs say it is "not strictly followed by Google for Jobs". |
| `exclude_job_publishers` | Comma list of publishers to drop. |
| `fields` | Field projection. |

The response has `status`, `request_id`, `parameters` (echoed back) and `data: {jobs: [...], cursor}`. It has **no total result count** [S2].

### GET /job-details [S1][S2]

Takes `job_id`, with up to 20 IDs comma separated. Each ID costs one credit. Also takes `country`, `language` and `fields`. It returns the search fields plus employer reviews, extra apply options and "estimated salaries for similar jobs". It also returns enrichment fields such as `seniority_level`, `required_experience_years`, `work_arrangement`, `industry`, `job_function` and `required_technologies`.

### GET /estimated-salary and GET /company-job-salary [S1][S2][S3]

These are aggregates keyed by title and location, not by posting. `/estimated-salary` takes `job_title`, `location`, `location_type` (`ANY`, `CITY`, `STATE`, `COUNTRY`) and `years_of_experience`. `/company-job-salary` also takes `company`. Each response has min, max and median salary, additional pay, `salary_period`, `salary_currency`, `salary_count` and `confidence`. The vendor sample shows `publisher_name: Glassdoor` and `salaries_updated_at`. All of this is **Estimated pay**.

## Mapping Fetch to /search-v2

| Fetch | JSearch |
|---|---|
| `title`, `location` | `query = "{title} in {location}"`, or `"{title}"` when the location is blank (country-wide). The FAQ warns that a query without a location returns fewer results [S3]. |
| `country` | `country`, plus `language` when the default is wrong. JSearch covers many more countries than `ADZUNA_CURRENCY` [S3], but `Fetch._known_country` limits a Run to the Adzuna list anyway. |
| `radius_km` | `radius`. Google treats it as a hint only. |
| `max_days_old` | Bucket it: 1 to `today`, up to 3 to `3days`, up to 7 to `week`, up to 30 to `month`, otherwise `all`. Then filter on `posted_at` on the client. |
| `category` | No equivalent. Ignore it. |
| `page` | The cursor is opaque, so page N needs pages 1 to N-1 first. The simplest option is one call with `num_pages = ceil(wanted / 10)`, which can return up to 200 jobs. Treat `page > 1` as already covered. The other option is to store the cursor from the previous page in the Store. |

`work_from_home` and `employment_types` match `HiringRequest.work_mode` and `employment_type`, but `Fetch` does not carry those fields today.

`Page.total` has nothing to read from, because the API returns no count. Use the number of postings returned so far, or treat it as unknown.

## Mapping a job to Posting

| Posting | JSearch field | Notes |
|---|---|---|
| `source` | new `Source.jsearch` | |
| `source_id` | `job_id` | In the spec examples this is Google's docid, e.g. `woj2gE2S_6LqvmLAAAAAAA==`, which also appears in `job_google_link` [S2]. The product page sample instead shows a long `job_id` and a short `job_uid` that looks like the docid [S3]. Prefer `job_uid` when present. It is not the publisher's own ID. |
| `title` | `job_title` | Required. |
| `company` | `employer_name` | Required. |
| `location` | `job_location` | Nullable. Fall back to joining city, state and country. |
| `region` | `(job_country, job_state, job_city)` with the nulls dropped | `job_country` is uppercase ISO2 [S2]. |
| `domain` | none | Search has no category. `job_onet_soc` exists, and `/job-details` has `industry` and `job_function`. |
| `posted_at` | `job_posted_at_timestamp` or `job_posted_at_datetime_utc` | Nullable. Drop the job when both are null. |
| `closes_at` | none | The v2 spec has no expiration field. The RapidAPI readme mentions "job expiration" for details [S4]. |
| `description` | `job_description` | Nullable. |
| `url` | `job_apply_link` | It carries `utm_campaign/utm_source/utm_medium=google_jobs_apply` [S2]. Strip those the way `adzuna._url` strips Adzuna's tracking. |
| `salary` | `job_min_salary`, `job_max_salary`, `job_salary_period` | See below. |

### Salary is Advertised

- The spec describes `job_min_salary` and `job_max_salary` as "parsed from the listing", `job_salary` as "as published by the source", and `job_salary_string` as "raw salary string as extracted from the listing" [S2].
- The FAQ says: "Salary fields are only populated when the employer explicitly includes salary data in the job posting. Most postings do not include salary data, so null values are expected." [S3]
- So `predicted=False`, and these salaries count as **Advertised pay** under GLOSSARY.md. The `/estimated-salary` and `/company-job-salary` figures, and the "estimated salaries for similar jobs" in `/job-details`, are **Estimated pay** and are not per-posting salaries.
- Period: `HOUR` maps to hourly, `DAY` to daily, `WEEK` to weekly, `MONTH` to monthly and `YEAR` to annual. Anything else maps to unknown.
- **The search response has no currency field** [S2]. Only the salary-estimate endpoints carry `salary_currency`. Take the currency from the Fetch country (`ADZUNA_CURRENCY[country]`). This is wrong for a job advertised in a foreign currency, so a check on `job_salary_string` may be worth adding.

## Data origin and Duplicates

- JSearch reads Google for Jobs, "the largest job aggregate on the web", which covers LinkedIn, Indeed, Glassdoor, ZipRecruiter, Monster, CareerBuilder, SimplyHired and employer career sites [S1][S4].
- Each job has a `job_publisher` and an `apply_options` list with one entry per publisher (`publisher`, `apply_link`, `is_direct`) [S2]. Google has already merged the copies across boards into one job. That cuts duplicates inside JSearch but not against Adzuna.
- Expect heavy overlap with Adzuna, which aggregates the same boards and employer sites. Adzuna listings themselves may also show up as an `apply_options` publisher (not verified). Duplicate detection against Adzuna has to use title, company, location and date, because no shared ID exists. You can sometimes parse the publisher's ID from an apply URL (`indeed.com/viewjob?jk=...`, `linkedin.com/jobs/view/...-<id>`), but the API does not offer it as a field.

## Quota, pricing and errors

Plans as listed on RapidAPI [S4] and on the vendor site [S3]:

| Plan | Price/month | Requests/month | Over quota | Rate limit |
|---|---|---|---|---|
| BASIC (free) | $0 | 200, hard limit, no card | blocked | 1000 requests/hour |
| PRO | $25 | 10,000, soft | $0.003 each | 5 rps |
| ULTRA | $75 | 50,000, soft | $0.002 each | 10 rps |
| MEGA | $150 | 200,000, soft | $0.001 each | 20 rps |
| Pay As You Go (vendor only) | none | metered | $0.005 each | 5 rps |

- Billing unit: "A call to any endpoint is one request. For search requests, each page returned by the API counts as a single request credit (up to 10 job listings)." [S4] A Run that wants 600 postings costs at least 60 credits, so the free tier covers about three such Runs a month.
- Quota headers, which every response carries [S4]: `x-ratelimit-requests-limit`, `x-ratelimit-requests-remaining` and `x-ratelimit-requests-reset` (seconds until the quota resets). `calls_left` should read `x-ratelimit-requests-remaining`. These are RapidAPI gateway headers, so the direct route may not send them (not verified).
- Errors [S4]: 400 for a missing or malformed parameter. 403 for "not subscribed to the API or your API key is invalid". 404 for a bad route. 429 for the rate limit or quota, with body `{"message":"Too many requests"}`. 5xx for server faults or timeouts. Backend errors use `{"status":"ERROR","request_id":...,"error":{"message","code"}}`. Gateway errors (403, 404, 429) use RapidAPI's own shape. Map 429 to `BudgetExhausted`, 403 to `SourceRejected`, and 5xx or timeouts to `SourceUnavailable`.

## Terms on caching, storage and attribution

- OpenWeb Ninja grants "a non-exclusive, non-transferable license to use, reproduce, and commercially exploit such API Data in your own products ... including for resale or redistribution as part of a broader product offering, provided that you do not resell, sublicense, or redistribute API Data as a standalone data or API product that substantially replicates the Services themselves." [S5]
- The terms also say: "You are solely responsible for ensuring that your use, storage, and redistribution of API Data complies with all applicable laws ..., third-party intellectual property rights, and any terms that apply to the original source of such data." [S5]
- The terms set no cache time limit and require no attribution. Caching and storing results for briefs is allowed. The risk sits with the original publishers' terms, which the vendor passes to us.
- The RapidAPI listing has `termsOfService: null` [S4]. RapidAPI's own terms defer to each provider's terms.

## Latency

- RapidAPI's score block for the API shows `avgLatency: 8525`, `avgServiceLevel: 99` and `avgSuccessRate: 99` [S4]. The unit is most likely milliseconds, so about 8.5 s per call on average.
- The vendor page says "within seconds or less" [S3].
- Plan for 5 to 15 s per search call, and more when `num_pages` is high. `gateway/http.py` sets `TIMEOUT = 10` seconds, which sits just above the 8.5 s average. Many JSearch calls would time out and retry, and each retry burns another credit. A JSearch client needs a longer timeout, around 30 s.
