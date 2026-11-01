# Research: JSearch on RapidAPI

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

What does JSearch (letscrape, on RapidAPI: <https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch>) offer as a jobs source?

- Endpoints that matter: Job Search, Job Details, and Estimated Salary or Company Job Salary if they exist. Parameters (query, page, num_pages, country, date_posted, remote, employment types, radius) and how they map onto `Fetch`.
- RapidAPI mechanics shared by every RapidAPI source: the `X-RapidAPI-Key` and `X-RapidAPI-Host` headers, quota headers (for example `x-ratelimit-requests-remaining`) that could feed `calls_left`, free-tier quota and price per plan, how overage is billed, and the error codes for quota and bad keys.
- Where its data comes from (Google for Jobs?), so Duplicates against Adzuna can be predicted. Does it return the original publisher's ID and URL?
- Field mapping to `Posting`. Salary: is it Advertised or the source's estimate? That decides how it lands under the Advertised and Estimated pay rule.
- Terms on caching and storing results, and attribution.
- Latency per call.

Docs and the RapidAPI playground pages are enough. A live call is optional and needs the key from [Subscribe to the job APIs and add keys](09-subscribe-to-the-job-apis.md). Capture findings in this ticket's Answer, with long notes in `../assets/`.

## Answer

Researched 2026-11-02. This answer comes from docs only, with no live call. The full notes, with field tables and quotes, are in [research-jsearch.md](../assets/research-jsearch.md).

### Recommendation

- Add JSearch as a source. Use the `/search-v2` endpoint and take `job_min_salary`, `job_max_salary` and `job_salary_period` as **Advertised pay** (`predicted=False`).
- Don't map `Fetch.page` onto the API. Send one call with `num_pages = ceil(wanted / 10)` (at most 20 pages, 200 jobs) and treat `page > 1` as already covered. The cursor is opaque, so page N would otherwise need N-1 earlier calls.
- Read `calls_left` from `x-ratelimit-requests-remaining`. Map 429 to `BudgetExhausted`, 403 to `SourceRejected`, and 5xx or a timeout to `SourceUnavailable`.
- Give JSearch a longer timeout, around 30 s. The shared `TIMEOUT = 10` in `gateway/http.py` is too close to the measured 8.5 s average, and each retry burns a credit.
- Take the salary currency from the Fetch country, because the search response has no currency field.
- Ignore `/estimated-salary` and `/company-job-salary` for Postings. They give Estimated pay per title and location, not per posting.
- Start on the free BASIC plan: 200 credits a month, hard capped, no card. That covers about three 600-posting Runs. PRO costs $25 for 10,000 credits.

### Key findings

- **Two routes, same API.** RapidAPI uses `https://jsearch.p.rapidapi.com` with the `X-RapidAPI-Key` and `X-RapidAPI-Host: jsearch.p.rapidapi.com` headers. OpenWeb Ninja direct uses `https://api.openwebninja.com/jsearch` with an `x-api-key` header. The vendor says both routes serve identical endpoints and response shapes. ([RapidAPI listing](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch), [vendor page](https://www.openwebninja.com/api/jsearch))
- **Endpoints.** RapidAPI lists four routes: `/search-v2`, `/job-details`, `/estimated-salary` and `/company-job-salary`. Search takes `query` (title and location as free text), `cursor`, `num_pages` (1 to 20), `country`, `language`, `date_posted` (`all`, `today`, `3days`, `week`, `month`), `work_from_home`, `employment_types`, `job_requirements`, `radius` (km, only a hint to Google), `exclude_job_publishers` and `fields`. **The response has no total count.** ([vendor llms.txt](https://www.openwebninja.com/api/jsearch/llms.txt), [OpenAPI spec](https://openwebninja.s3.us-east-1.amazonaws.com/portal/openapi/jsearch.yaml))
- **Fetch mapping.** The query is `"{title} in {location}"`, or the title alone when the search is country-wide. `max_days_old` maps to the nearest `date_posted` bucket, with a client-side filter after. `radius_km` maps to `radius`. `category` has no equivalent.
- **Data origin.** JSearch reads Google for Jobs, which covers LinkedIn, Indeed, Glassdoor, ZipRecruiter, Monster, employer sites and more. Expect heavy Duplicates against Adzuna. `job_id` is Google's docid, not the publisher's ID. The publisher's URL comes through as `job_apply_link`, and `apply_options` lists one link per publisher. Both carry `utm_*=google_jobs_apply` tracking, which should be stripped. ([OpenAPI spec](https://openwebninja.s3.us-east-1.amazonaws.com/portal/openapi/jsearch.yaml))
- **Salary is Advertised.** The spec says the fields are "parsed from the listing", and the FAQ says "Salary fields are only populated when the employer explicitly includes salary data in the job posting." Periods are `HOUR`, `DAY`, `WEEK`, `MONTH` and `YEAR`. ([vendor page FAQ](https://www.openwebninja.com/api/jsearch))
- **Posting mapping.** `job_title` maps to title, `employer_name` to company, `job_location` to location, `(job_country, job_state, job_city)` to region, and `job_posted_at_timestamp` to `posted_at`. `job_description` maps to description and `job_apply_link` to url. Domain and `closes_at` have no source field.
- **Quota and pricing.** BASIC is $0 for 200 requests a month, hard capped, at 1000 requests an hour. PRO is $25 for 10k plus $0.003 per extra request, at 5 rps. ULTRA is $75 for 50k plus $0.002, at 10 rps. MEGA is $150 for 200k plus $0.001, at 20 rps. Each search page of up to 10 jobs costs one credit. The headers are `x-ratelimit-requests-limit`, `-remaining` and `-reset`. ([RapidAPI listing](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch), [vendor page](https://www.openwebninja.com/api/jsearch))
- **Errors.** The API returns 400 for a bad parameter, 403 when you aren't subscribed or the key is invalid, 429 with `{"message":"Too many requests"}` for the rate limit or quota, and 5xx for server faults. ([RapidAPI listing readme](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch))
- **Terms.** You may use, store and redistribute the data inside your own product, but not resell it as a standalone data feed. You alone answer for compliance with the original publishers' terms. The terms set no cache limit and require no attribution. ([OpenWeb Ninja terms](https://www.openwebninja.com/terms))
- **Latency.** RapidAPI reports `avgLatency 8525` (about 8.5 s), with a 99% success rate. ([RapidAPI listing](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch))

### Not verified

- Anything from a live call. The real latency, the actual response shape and whether `job_uid` appears are all unchecked.
- Whether `job_id` stays stable across calls. The vendor sample shows a long `job_id` next to a short `job_uid`, while the spec examples show only the short docid.
- Whether the old `/search` endpoint with a `page` parameter still answers on RapidAPI. It is not in the endpoint list.
- Whether the direct `api.openwebninja.com` route sends the same `x-ratelimit-*` headers as RapidAPI.
- What RapidAPI's gateway returns for a missing key, as opposed to an invalid one (likely 401 versus 403).
- Whether a salary in a foreign currency, or a salary Google estimated rather than the employer, ever reaches `job_min_salary` and `job_max_salary`.
- How often Adzuna listings appear as an `apply_options` publisher.
- That `avgLatency` is in milliseconds.
