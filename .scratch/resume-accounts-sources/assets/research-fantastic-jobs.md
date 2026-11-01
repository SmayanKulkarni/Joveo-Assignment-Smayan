# Fantastic Jobs research notes (Active Jobs DB and LinkedIn Job Search API)

Researched 2026-11-02, from docs only. There was no key, so no live call.

## Sources

- [S1] Developer portal home and doc index: <https://developer.fantastic.jobs>, <https://developer.fantastic.jobs/llms.txt>. Every doc page also has a `.md` twin (for example `/documentation/credit-usage.md`), which is what I read.
- [S2] New Jobs endpoint guide: <https://developer.fantastic.jobs/documentation/endpoints/new-jobs>
- [S3] Plans, Limits & Upgrades: <https://developer.fantastic.jobs/documentation/credit-usage>
- [S4] OpenAPI spec (v1): <https://data.fantastic.jobs/openapi>
- [S5] Public plan catalogue behind the portal's pricing page: `https://api.zuploedge.com/v3/zudoku-metering/fantastic-jobs-main-896a7f4/pricing-page`. The pricing page (<https://developer.fantastic.jobs/pricing>) renders this JSON client-side, so WebFetch sees no numbers. I found the URL in the portal's JS bundle and fetched it without a login.
- [S6] Terms & Conditions, last updated May 19, 2026: <https://developer.fantastic.jobs/terms>
- [S7] FAQ (deduplication, timeouts): <https://developer.fantastic.jobs/faq>
- [S8] Changelog, including "v1 - Migrating from Rapid and api.fantastic.jobs": <https://developer.fantastic.jobs/changelog>
- [S9] Time Fields: <https://developer.fantastic.jobs/documentation/time-fields>
- [S10] Nuances of Location Search: <https://developer.fantastic.jobs/documentation/nuances-of-location-search>
- [S11] Enrichments: <https://developer.fantastic.jobs/documentation/enrichments>
- [S12] Country Job Statistics, last updated October 27, 2026: <https://developer.fantastic.jobs/documentation/country-job-statistics>
- [S13] How Fantastic.jobs API Works: <https://developer.fantastic.jobs/documentation/how-fantastic-jobs-api-works>
- [S14] Sample payloads (100 rows each): <https://files.fantastic.jobs/sample-ats.json>, <https://files.fantastic.jobs/sample-jb.json>
- [S15] RapidAPI listing, Active Jobs DB: <https://rapidapi.com/fantastic-jobs-fantastic-jobs-default/api/active-jobs-db> (and `/pricing`)
- [S16] RapidAPI listing, LinkedIn Job Search API: <https://rapidapi.com/fantastic-jobs-fantastic-jobs-default/api/linkedin-job-search-api> (and `/pricing`)
- [S17] LinkedIn User Agreement, effective November 3, 2025: <https://www.linkedin.com/legal/user-agreement>

WebFetch shows only the title of the RapidAPI pages. I fetched the raw HTML with curl and decoded the embedded Next.js payload to read the readme, endpoint list and billing plans.

## Same API, two storefronts

Both RapidAPI listings are thin wrappers over the same v1 API that the developer portal sells.

- The portal changelog calls v1 "Migrating from Rapid and api.fantastic.jobs" [S8]. The old split endpoints (`active-ats-1h`, `-24h`, `-7d`, `-6m`, and `active-jb-hourly` etc.) became one `active-ats` and one `active-jb` with a `time_frame` parameter.
- The RapidAPI listings already show the v1 routes and v1 parameter names [S15][S16]:
  - Active Jobs DB (`active-jobs-db.p.rapidapi.com`): `/active-ats`, `/active-ats-count`, `/expired-ats`, `/ats-organizations`.
  - LinkedIn Job Search API (`linkedin-job-search-api.p.rapidapi.com`): `/active-jb`, `/active-jb-count`, `/expired-jb`.
- So "Active Jobs DB" = the ATS feed (company career sites) and "LinkedIn Job Search API" = the job board feed. On RapidAPI they are two products with two subscriptions. On the portal one key and one quota cover both feeds [S3].
- Auth differs. RapidAPI uses `X-RapidAPI-Key` plus `X-RapidAPI-Host`. Direct uses `Authorization: Bearer <key>` against `https://data.fantastic.jobs/v1/...` [S1][S4].
- Quota headers differ. RapidAPI: `x-ratelimit-jobs-limit`, `x-ratelimit-jobs-remaining`, `x-ratelimit-requests-limit`, `x-ratelimit-requests-remaining`, `x-ratelimit-jobs-reset` (seconds) [S15]. Direct: `x-api-jobs-this-request`, `x-api-jobs-remaining`, `x-api-jobs-limit`, `x-api-requests-remaining`, `x-api-requests-limit`, `x-api-next-billing-date`; the `remaining` values are cached for a few seconds, `x-api-jobs-this-request` is exact [S3].

## Endpoints and time windows

| `time_frame` | Window | Ingestion delay | Pagination |
| --- | --- | --- | --- |
| `1h` | Jobs indexed in one clock hour, served an hour late (a 09:15 call gets 07:00 to 08:00) | 1 h | offset |
| `24h` | Rolling 24 h, same one-hour lag | 1 h | offset |
| `7d` | Rolling 7 days, refreshed every 1 to 3 minutes | about 45 min | offset |
| `6m` | Rolling 6 months, refreshed every 1 to 3 minutes | about 45 min | cursor (offset works but is slow deep in) |

Source: [S2][S9]. `time_frame` is required, default `24h` [S4]. Expired jobs are removed from the `7d` and `6m` windows, so those return currently active jobs only [S1 llms.txt, Expired Jobs].

Other endpoints:
- `active-ats-count` / `active-jb-count` (beta): `{count}` for a filter set. One API Request, zero Jobs credits. Also take `time_frame=1m` (last 31 days, including expired jobs) [S8][S4].
- `expired-ats` / `expired-jb`: arrays of expired internal IDs, `1h`, `1d`, `1m`, `6m`. `expired-jb` covers LinkedIn only [S2].
- `modified-ats`: ATS jobs whose tracked fields changed in the last 24 h (Pro plans only) [S3].
- `ats-organizations` (about 50 MB catalogue) and `ats-organizations-advanced` (beta, Pro-100k and up) [S1].

## Filters (both feeds unless noted) [S2][S4]

- Text: `title`, `description` (searches title and description together; not allowed on `active-jb` with `6m`), `location`, `organization` (exact, case-sensitive), and Boolean `_advanced` versions of each. Google-style syntax: `"exact phrase"`, `a OR b`, `-word`. No synonyms, stemming beyond full-text, or semantic search [S13]. `C++`, `C#` and `.NET` collapse to their letters [S7].
- Dates: `date_posted_gte`, `date_posted_lt`, `date_created_gte`, `date_created_lt` (ISO 8601, UTC).
- Source and org: `source`, `exclude_source`, `domain` (ATS only), `organization_industry` (exact LinkedIn industry), `organization_slug`, headcount and size buckets, `organization_funding_*` (ATS only), `organization_agency=only|exclude`.
- AI-derived: `ai_experience_level` (`0-2`, `2-5`, `5-10`, `10+`), `ai_work_arrangement` (`On-site`, `Hybrid`, `Remote OK`, `Remote Solely`), `ai_employment_type`, `ai_language`, `ai_education`, `ai_taxonomies_a_primary` / `ai_taxonomies_a` (33 fixed values such as `Technology`, `Healthcare`, `Finance & Accounting`), `ai_visa_sponsorship`.
- Other: `has_salary=true`, `has_no_location`, `seniority` (LinkedIn's own, JB only), `direct_apply` (JB only), `exclude_ats_duplicate` (JB only), `linkedin_id` (JB only), `id`.
- The old `remote` filter is gone; use `ai_work_arrangement` [S8].
- No radius or geo-distance filter exists. `lats_derived` and `lngs_derived` are returned, so a radius could be applied client-side.
- Request URL must stay under 10,000 characters; requests time out after 60 s [S7].

## Pagination and page size

- `limit` default 100, min 1, max 1000. `offset` for `1h`/`24h`/`7d`; `cursor` (last `id`, orders by `id` ascending instead of `date_posted` descending) for `6m` [S2].
- The response is a bare JSON array with **no total count** [S4]. Loop until fewer than `limit` rows come back, or call the count endpoint (one request, zero jobs) to get a total.
- Errors: 400 with an RFC 7807 problem body, 429 for rate limit or quota, 504 when the query exceeds the server-side timeout [S4]. 401/403 are not listed in the spec.

## Mapping onto `Fetch`

| `Fetch` field | Fantastic Jobs | Note |
| --- | --- | --- |
| `title` | `title="\"<title>\""` | Quote it for a phrase match, the same intent as Adzuna's `title_only`. |
| `country` | part of `location` | Needs a code to English-name map (`gb` to `United Kingdom`, `us` to `United States`). Abbreviations do not match [S10]. |
| `location` | `location` or `location_advanced` | Stored as `City, Region, Country` in English (`Munich`, not `Muenchen`). Docs advise quoting the full string with country, e.g. `"London, England, United Kingdom"` [S10]. Our bare place names need the country added; `location_advanced='Austin' & 'United States'` should work (not verified). |
| `radius_km` | none | Client-side filter on `lats_derived`/`lngs_derived`, or ignore. |
| `max_days_old` | `date_posted_gte = today - N` with `time_frame=7d` when N <= 7, else `6m` | `date_posted` is what the source shows; it can be earlier than `date_created` [S9]. |
| `category` | none directly | `ai_taxonomies_a_primary` uses a different 33-value list. Mapping Adzuna tags onto it is possible but lossy; simplest is to ignore `category` for this source. |
| `page` | `offset = (page - 1) * limit` | Fine for `7d`. For `6m` offset is allowed but docs prefer cursor; with a date filter and small pages it should be acceptable (not verified). |

Each call must send `description_format=text`, or the description field is omitted [S2].

## Mapping onto `Posting`

| `Posting` | ATS feed (`active-ats`) | JB feed (`active-jb`) |
| --- | --- | --- |
| `source` | new `Source` member | new `Source` member |
| `source_id` | `str(id)` (int64, unique per URL) | `str(id)`; `linkedin_id` is LinkedIn's posting ID |
| `title` | `title` | `title` |
| `company` | `organization` | `organization` |
| `location` | `locations_derived[0]` | `locations_derived[0]` |
| `region` | `(countries_derived[0], regions_derived[0], cities_derived[0])`, dropping blanks | same |
| `domain` | `ai_taxonomies_a[0]` | same |
| `posted_at` | `date_posted` (UTC, no zone suffix), fallback `date_created` | same |
| `closes_at` | `date_valid_through` | same |
| `description` | `description_text` | `description_text` |
| `url` | `url` (the employer's ATS page) | `url` (a LinkedIn job URL) |
| `salary` | `ai_salary_*` | `ai_salary_*` |

Sources: [S4] field list, [S14] samples.

- The region order matches Adzuna's `area`, which starts at the country. The derived arrays hold one entry per location, so a multi-location job keeps only its first.
- `cities_derived` is null when only a county was found; `counties_derived` is then set [S10][S4].
- Timestamps in the samples look like `2026-11-01T00:27:57` with no zone; docs say all timestamps are UTC [S9][S14].

### Salary

- Source fields: `salary` (raw schema.org object from the source, "often partial or missing") and `ai_salary_currency` (ISO 4217), `ai_salary_value` (single figure), `ai_salary_min_value`, `ai_salary_max_value`, `ai_salary_unit_text` (`HOUR`, `DAY`, `WEEK`, `MONTH`, `YEAR`) [S4].
- The AI fields are extracted by an LLM from the job's own title, description, location and page elements. "No outside information is included in this process" [S11]. That makes them **Advertised pay** (`predicted=False`): a figure the employer wrote, read by a model. They are not Estimated pay.
- When only `ai_salary_value` is set, use it as both min and max. Map the unit to `PayPeriod` (`YEAR` to `annual`, `MONTH` to `monthly`, `WEEK` to `weekly`, `DAY` to `daily`, `HOUR` to `hourly`). Unlike Adzuna, the currency comes from the posting.
- Coverage in the samples: ATS 61/100 had `ai_salary_currency`, 0/100 had raw `salary`; JB 83/100 AI salary, 63/100 raw [S14]. The ATS sample is US-heavy, where pay-transparency laws push salaries into descriptions, so expect less elsewhere.
- Terms §1.4 says `ai_*` fields "may contain inaccuracies" and names compensation benchmarking as a use the customer must validate [S6].

## Data origin, overlap and ID stability

- ATS feed: 58 ATS platforms (Greenhouse, Lever, Workday, Ashby, iCIMS, SmartRecruiters, BambooHR and more) across 200,000+ companies, plus Google, Meta, Apple and Amazon, polled hourly [S13]. RapidAPI says "over 275,000 organizations" [S15]. The URL is the employer's own page.
- JB feed: LinkedIn (hourly for the US, UK, CA, NZ, AU, SG and IE; other countries every few hours or less), plus Wellfound and Y Combinator [S2]. The RapidAPI LinkedIn listing describes itself as LinkedIn only; whether `source=wellfound` works there is not verified.
- Deduplication: every job is unique by URL; ATS jobs with the same title, organization, description, locations and location requirements are content duplicates [S7]. `exclude_ats_duplicate=true` drops JB jobs matched to an ATS job by title + org + country or title + LinkedIn company + country. It is precision-first and misses some [S7][S8].
- ATS vs JB overlap, from the country table [S12]: US ATS 1.8M to 2.2M a month, JB 3.7M to 4.5M, combined (deduplicated) 4.3M to 5.2M. So roughly 1.2M to 1.5M jobs a month appear in both, about a third of the JB feed and about two thirds of the ATS feed. UK: ATS 140K to 170K, JB 420K to 510K, combined 470K to 570K (similar ratio). India: ATS 100K to 130K, JB 350K to 420K, combined 400K to 480K. Germany: ATS 89K to 110K, JB 530K to 640K.
- Overlap with Adzuna is not published. Adzuna aggregates job boards and employer sites, so expect real Duplicates; there is no shared ID, so title, company, location and date matching is the only way.
- `id` is the key for expiry and modification matching across calls [S2], so it is stable within Fantastic Jobs. v1 changed its type from string to bigint [S8]; whether the numeric value stayed the same is not stated. `linkedin_id` is LinkedIn's own posting ID and is the better cross-source key for LinkedIn jobs.

## Quota and how it is counted

Two meters on both storefronts [S3][S15][S16]:
- **Jobs**: one credit per job returned by `active-ats` / `active-jb`. Count, expired, modified and organisation endpoints cost zero Jobs.
- **Requests**: one per call to any endpoint.
- Most plans give half as many Requests as Jobs, so Jobs runs out first "by design" [S15]. Requests are a hard cap everywhere; only the big direct plans allow Jobs overage.
- Calling the same window twice pays twice. The terms refuse refunds for duplicate pulls (§7.2) [S6].
- For us, the cost of a Run is about the number of jobs it pulls. A 600-posting Run costs about 600 Jobs credits, plus some for postings later judged irrelevant.

## Pricing

### Direct (developer portal) [S5][S3]

| Plan | USD / month | Jobs | Requests | Extras |
| --- | --- | --- | --- | --- |
| Free 14-day Trial | 0, no card | 500 (per 14 days, once) | 100 | count endpoints included [S12] |
| Starter-5 | 45 | 5,000 | 2,500 | basic org enrichment |
| Starter-20k | 95 | 20,000 | 10,000 | + expired |
| Pro-50k | 175 | 50,000 | 25,000 | + modified |
| Pro-100k | 250 | 100,000 (then $0.0025/job) | 50,000 | + advanced org (beta) |
| Pro-250k | 500 | 250,000 (then $0.002) | 125,000 | |
| Pro-500k | 900 | 500,000 (then $0.0018) | 250,000 | |
| Pro-1m | 1,600 | 1,000,000 (then $0.0016) | 500,000 | |
| Pro-2m | 2,800 | 2,000,000 (then $0.0014) | 1,000,000 | |

- Yearly price is 12 times monthly (no discount). Prices exclude tax. 600 requests a minute on every plan [S3][S6].
- The quota covers both feeds, so one subscription gives ATS and LinkedIn jobs.
- I found no plan gating on `time_frame` in the portal docs; only expired, modified and advanced org are gated [S3].

### RapidAPI, Active Jobs DB [S15]

| Plan | USD / month | Jobs | Requests | Rate | Features |
| --- | --- | --- | --- | --- | --- |
| BASIC | 0 | 250 | 25 | | expired |
| PRO | 45 | 5,000 | 2,500 | 2/s | expired |
| ULTRA | 95 | 20,000 | 10,000 | 5/s | expired, modified, "Hourly Firehose", "Backfill" |
| MEGA | 175 | 50,000 | 25,000 | 10/s | same as ULTRA |

All limits hard, no overage. The feature text says the "Hourly Firehose API" (`1h`) and "Backfill API" (6 months) are "for Ultra & Mega users".

### RapidAPI, LinkedIn Job Search API [S16]

| Plan | USD / month | Jobs | Requests | Rate | Features |
| --- | --- | --- | --- | --- | --- |
| BASIC | 0 | 250 | 25 | | expired |
| PRO | 45 | 10,000 | 5,000 | 5/s | expired |
| ULTRA | 95 | 20,000 | 10,000 | 15/s | expired, "Hourly Firehouse" |
| MEGA | 175 | 50,000 | 25,000 | 25/s | same as ULTRA |

All limits hard, no overage. No "Backfill" feature is listed for this product.

### Comparison

- Same prices at $45, $95 and $175 for the ATS feed. LinkedIn PRO on RapidAPI gives 10,000 jobs for $45, double the direct Starter-5.
- RapidAPI BASIC is free every month (250 jobs, 25 calls, per product, so 500 jobs across both). The direct trial is 500 jobs once, for 14 days.
- Direct is cheaper if we want both feeds: $45 buys 5,000 jobs across ATS and LinkedIn, against $90 for two RapidAPI PRO plans.
- Direct appears to allow `6m` on every plan. RapidAPI's ATS listing suggests `1h` and 6-month backfill need ULTRA or MEGA, which would cap `max_days_old` at 7 on BASIC and PRO.
- At our scale (a few Runs of up to 600 postings), the free tiers cover one or two Runs a month at most.

## Terms

Fantastic Jobs [S6]:
- §1.3: Fantastic Jobs is an aggregator, claims no ownership of the job data, and "You are responsible for ensuring Your use of the data complies with any applicable terms imposed by the original source."
- §9.1 and §9.2: no competing job-data service and no reselling or redistributing the raw data as a standalone product. "Using the data internally or to power features within Your own product ... is permitted."
- No clause limits storage or caching, and none requires attribution. The docs actively recommend storing results in your own database [S13].
- §1.4: AI-derived fields carry no accuracy warranty; compensation benchmarking is named as a use to validate.
- §8: `description_format=html` is raw, unsanitised third-party HTML. Use `text`.
- No uptime SLA (§1.2). Dutch law, Amsterdam courts.

LinkedIn [S17]:
- User Agreement §8.2 bars using software "to scrape or copy the Services, including profiles and other data", and bars copying, using, displaying or distributing "any information (including content) obtained from the Services, whether directly or through a third party" without the content owner's consent. It also bars monetising LinkedIn data.
- Fantastic Jobs indexes LinkedIn without a LinkedIn partnership that I could find, and §1.3 puts compliance on the customer. Storing LinkedIn postings in our cache and showing them as evidence in a Brief is the kind of reuse §8.2 targets. The risk sits with us, not with Fantastic Jobs.
- The ATS feed carries no such conflict: it reads employers' public career pages, and the URLs go back to the employer.

RapidAPI's own terms apply on top for the RapidAPI route; I did not read them, and neither listing links provider-specific terms.
