# Research: Fantastic Jobs APIs (Active Jobs DB and LinkedIn Job Search API)

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

What do Fantastic Jobs' two APIs offer, and how do the RapidAPI listings compare with buying direct?

- Active Jobs DB (<https://rapidapi.com/fantastic-jobs-fantastic-jobs-default/api/active-jobs-db>) and LinkedIn Job Search API (<https://rapidapi.com/fantastic-jobs-fantastic-jobs-default/api/linkedin-job-search-api>): endpoints (for example the 1h, 24h and 7d windows), filters (title, location, description, organisation, remote, date), page size and offset, and how they map onto `Fetch`.
- The direct developer portal (<https://developer.fantastic.jobs>): is it the same data under a different plan, and is its free tier or pricing better than RapidAPI's? The user's subscription page there needs their login, so judge from the public docs.
- Where the data comes from (ATS career sites; LinkedIn), how much the two overlap with each other and with Adzuna, and whether a `source_id` stays stable.
- Field mapping to `Posting`, including salary (Advertised or estimated), the location hierarchy for `region`, and any domain or category.
- Quota and price per tier, how quota is counted (per call or per job returned), and the terms on storing and caching results. Note anything about LinkedIn data that limits reuse.

Docs and playgrounds are enough. A live call needs the key from [Subscribe to the job APIs and add keys](09-subscribe-to-the-job-apis.md). Capture findings in this ticket's Answer, with long notes in `../assets/`.

## Answer

Researched 2026-11-02. This answer comes from docs only, with no live call. The full notes, with field tables, plan tables and sources, are in [research-fantastic-jobs.md](../assets/research-fantastic-jobs.md).

### Recommendation

- Add the **ATS feed** (Active Jobs DB, `active-ats`) as a source. It reads employers' own career pages, has Advertised pay in most US postings, and has no terms conflict.
- Leave the **LinkedIn feed** (`active-jb`) out for now. Nearly everything it adds over the ATS feed is LinkedIn data, which LinkedIn's User Agreement forbids reusing, and Fantastic Jobs' terms put that risk on us. If it goes in later, send `exclude_ats_duplicate=true`.
- Buy **direct** if both feeds are wanted. One key and one Jobs quota cover both, and `6m` appears open on every plan. Stay on **RapidAPI** if only the ATS feed is wanted and the free BASIC plan is enough. It renews monthly (250 jobs, 25 calls), while the direct trial is 500 jobs once.
- Per call: `time_frame=7d` when `max_days_old <= 7`, else `6m`, plus `date_posted_gte`, `title="\"<title>\""`, `location` written as English full names with the country, `description_format=text` (or no description comes back), and `offset = (page - 1) * limit`.
- Map `ai_salary_*` to **Advertised pay** (`predicted=False`), with the currency from `ai_salary_currency`. Take `region` from `countries_derived`, `regions_derived` and `cities_derived`, and `domain` from `ai_taxonomies_a[0]`.
- Drop `radius_km` and `category` for this source. There is no radius filter, and the taxonomy is not Adzuna's.
- Budget by **jobs returned**, not calls. A 600-posting Run costs about 600 Jobs credits. Set `calls_left` from the jobs-remaining header divided by `limit`.

### Key findings

- **Same API, two storefronts.** The portal changelog's v1 section is titled "Migrating from Rapid and api.fantastic.jobs". Both RapidAPI listings now expose the v1 routes: Active Jobs DB is `/active-ats` and LinkedIn Job Search API is `/active-jb`, each with count and expired endpoints. Auth is `X-RapidAPI-Key` on RapidAPI and `Authorization: Bearer` against `https://data.fantastic.jobs/v1` direct. ([changelog](https://developer.fantastic.jobs/changelog), [Active Jobs DB](https://rapidapi.com/fantastic-jobs-fantastic-jobs-default/api/active-jobs-db), [LinkedIn Job Search API](https://rapidapi.com/fantastic-jobs-fantastic-jobs-default/api/linkedin-job-search-api), [OpenAPI](https://data.fantastic.jobs/openapi))
- **Time windows.** `time_frame` is required and takes four values. `1h` gives one clock hour, served an hour late. `24h` is rolling, with the same lag. `7d` and `6m` are rolling and about 45 minutes behind. `7d` and `6m` drop expired jobs. Offset pagination is for `1h`, `24h` and `7d`, and cursor pagination is for `6m`. `limit` runs from 1 to 1000 (default 100). **The response is a bare array with no total.** `active-ats-count` returns one for 1 request and 0 jobs. ([New Jobs](https://developer.fantastic.jobs/documentation/endpoints/new-jobs), [Time Fields](https://developer.fantastic.jobs/documentation/time-fields))
- **Filters.** Title, description, location and organisation, with Boolean `_advanced` versions. Also `date_posted_*` and `date_created_*`, `source`, LinkedIn industry, headcount, `ai_work_arrangement` (this replaced `remote`), `ai_experience_level`, `ai_employment_type`, `ai_taxonomies_a_primary`, `has_salary`, `seniority` (JB only) and `exclude_ats_duplicate` (JB only). There is no radius filter, and no synonyms or semantic search. Locations must be English full names like `"London, England, United Kingdom"`, with no country codes. ([New Jobs](https://developer.fantastic.jobs/documentation/endpoints/new-jobs), [location nuances](https://developer.fantastic.jobs/documentation/nuances-of-location-search))
- **Salary is Advertised.** `ai_salary_value`, `_min_value`, `_max_value`, `_currency` and `_unit_text` (`HOUR` to `YEAR`) are extracted by an LLM from the posting itself, with "No outside information". The raw `salary` field is often missing. In the samples, 61 of 100 ATS rows and 83 of 100 LinkedIn rows had an AI salary, and the ATS rows were mostly US. The terms disclaim accuracy for `ai_*` fields and name compensation benchmarking as a use to validate. ([Enrichments](https://developer.fantastic.jobs/documentation/enrichments), [samples](https://files.fantastic.jobs/sample-ats.json), [terms §1.4](https://developer.fantastic.jobs/terms))
- **Posting mapping.** `id` maps to source_id, `title` to title, `organization` to company, `locations_derived[0]` to location, and `(countries_derived, regions_derived, cities_derived)` to region (country first, like Adzuna's `area`). `ai_taxonomies_a[0]` maps to domain, `date_posted` (UTC) to posted_at, `date_valid_through` to closes_at, `description_text` to description, and `url` to url. ([OpenAPI](https://data.fantastic.jobs/openapi))
- **Data origin and overlap.** The ATS feed covers 58 ATS platforms, 200,000+ companies, plus Google, Meta, Apple and Amazon, polled hourly. The JB feed is LinkedIn (hourly in US, UK, CA, NZ, AU, SG and IE, slower elsewhere), plus Wellfound and Y Combinator. From the country table, about a third of US LinkedIn jobs are also in the ATS feed, which is about two thirds of the ATS feed. The UK ratio is similar. Overlap with Adzuna is not published, so expect Duplicates matched on title, company, location and date. `id` is unique per URL and is the key for expiry across calls, so it is stable. `linkedin_id` is LinkedIn's own posting ID. ([How it works](https://developer.fantastic.jobs/documentation/how-fantastic-jobs-api-works), [FAQ](https://developer.fantastic.jobs/faq), [country stats](https://developer.fantastic.jobs/documentation/country-job-statistics))
- **Quota is per job returned.** Each job from `active-ats` or `active-jb` costs one Jobs credit, and each call costs one Request. Count, expired and modified calls cost no Jobs credits. Requests are hard-capped on every plan. Pulling the same window twice pays twice, with no refund. ([Plans, Limits & Upgrades](https://developer.fantastic.jobs/documentation/credit-usage), [terms §7.2](https://developer.fantastic.jobs/terms))
- **Direct pricing.** These figures come from the portal's public plan JSON, because the page renders client-side. Free 14-day trial: 500 jobs and 100 requests, no card. Starter-5: $45 for 5k jobs. Starter-20k: $95 for 20k, and adds expired. Pro-50k: $175 for 50k, and adds modified. Pro-100k: $250 for 100k, then $0.0025 a job. Plans go up to Pro-2m at $2,800. The limit is 600 requests a minute, and one quota covers both feeds. ([pricing JSON](https://api.zuploedge.com/v3/zudoku-metering/fantastic-jobs-main-896a7f4/pricing-page), [pricing page](https://developer.fantastic.jobs/pricing))
- **RapidAPI pricing.** All limits are hard, with no overage. Active Jobs DB: BASIC $0 (250 jobs, 25 requests a month), PRO $45 (5k), ULTRA $95 (20k), MEGA $175 (50k). The listing says the hourly firehose and the 6-month backfill are "for Ultra & Mega users". LinkedIn Job Search API: BASIC $0 (250 jobs, 25 requests), PRO $45 (10k, double the direct Starter-5), ULTRA $95 (20k), MEGA $175 (50k). Each is a separate subscription. ([Active Jobs DB pricing](https://rapidapi.com/fantastic-jobs-fantastic-jobs-default/api/active-jobs-db/pricing), [LinkedIn pricing](https://rapidapi.com/fantastic-jobs-fantastic-jobs-default/api/linkedin-job-search-api/pricing))
- **Terms.** Storing the data and using it inside our own product is allowed. Reselling it or running a competing data feed is not (§9.1, §9.2). No clause limits caching, and none requires attribution. Under §1.3 we alone answer for the original sources' terms. ([terms](https://developer.fantastic.jobs/terms))
- **LinkedIn data.** LinkedIn's User Agreement §8.2 bars copying, using, displaying or distributing "any information (including content) obtained from the Services, whether directly or through a third party" without consent, and bars scraping. Caching LinkedIn postings and citing them in Briefs falls under that. ([LinkedIn User Agreement](https://www.linkedin.com/legal/user-agreement))

### Not verified

- Anything from a live call, including the real response shape, latency and error bodies for a missing or invalid key (the spec lists only 400, 429 and 504).
- Whether RapidAPI BASIC and PRO really refuse `time_frame=1h` and `6m`. This comes from the plan feature text, not from a call. If they do, `max_days_old` is capped at 7 there.
- Whether the direct trial and Starter plans allow `6m`. The docs list no gate, but they don't say so outright.
- Whether offset paging on `6m` with a `date_posted_gte` filter stays fast at our page depths.
- Whether `location_advanced='<place>' & '<country>'` matches our bare place names as hoped.
- Whether `id` values kept their numbers when v1 changed the type from string to bigint.
- Whether the RapidAPI LinkedIn listing also serves Wellfound and Y Combinator through `source`.
- How much of either feed duplicates Adzuna.
- Whether RapidAPI BASIC needs a card, and RapidAPI's own terms on top of Fantastic Jobs' terms.

## Out of scope

On 2026-11-02 the user dropped every RapidAPI source and kept only Arbeitnow. This research stays as a record and feeds no decision.
