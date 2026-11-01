# Research: Arbeitnow job board API

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

What does the Arbeitnow job board API offer, and how would it map onto a `Posting` and a `Fetch`?

- Endpoints, auth (if any), pagination, page size, rate limits and terms of use, including attribution and caching.
- Which `Fetch` fields it can honour: title search, country, location, radius, date range, category. If it has no server-side search, how many pages a client would need to filter locally, and how fresh the feed is.
- Coverage: countries (it looks Germany and Europe focused), remote jobs, and volume per day.
- Field mapping to `Posting` (`kernel/types.py`): `source_id`, company, location and `region`, `domain` (from tags?), `posted_at`, `closes_at`, description (HTML?), URL, salary (any at all, Advertised or not).
- A live call from a throwaway script outside the repo, if it needs no key, recording one real response shape.

Capture findings in this ticket's Answer, with long notes in `../assets/`.

## Answer

Researched 2026-11-02. Long notes, the live response shape and the full mapping tables are in [research-arbeitnow.md](../assets/research-arbeitnow.md).

### Recommendation

- Usable as a keyless, extra source for Germany, the UK, France, Switzerland and the Netherlands (`de`, `gb`, `fr`, `ch`, `nl`) only. Other countries get no results.
- Walk the whole feed once (about 21 pages, about 35 MB), cache that snapshot for about an hour, and answer every `Fetch` by filtering locally. No search runs server-side.
- Map `salary`, `closes_at` and `domain` to `None`. Use `slug` as `source_id` and take the country from the job URL's host.
- Add a visible link back to arbeitnow.com, as ToS section 11 requires. Before relying on it in a public deployment, ask Arbeitnow whether section 2's "personal, non-commercial" license applies to API users.

### Key findings

- **Endpoint and auth.** `GET https://www.arbeitnow.com/api/job-board-api`, no key ([blog](https://www.arbeitnow.com/blog/job-board-api), [Postman docs](https://documenter.getpostman.com/view/18545278/UVJbJdKh)). A live call succeeded with no headers.
- **Shape.** `{data, links, meta}`. Each item has exactly `slug, company_name, title, description (HTML), remote, url, tags, job_types, location, created_at (Unix seconds)`. That is the same schema as the 2021 Postman sample. There is no salary, closing date, country, category or coordinates.
- **Pagination.** `?page=N`, walked until `data` is empty (page 22 on 2026-11-01). Each page merges up to 100 jobs from arbeitnow.com (DE) and 50 each from .co.uk, .fr, .ch and .nl, so page 1 has 300. `meta.per_page/from/to` are unreliable. Order is only roughly by `created_at`, so a client cannot stop early at a date cutoff. All observed live.
- **Filters.** Only `visa_sponsorship=true` works ([blog](https://www.arbeitnow.com/blog/job-board-api)). `search`, `location`, `remote` and `tags` were tested live and ignored. Of the `Fetch` fields, `title`, `country`, `location` and `max_days_old` can be met by local filtering. `radius_km` and `category` cannot.
- **Freshness and rate limits.** `meta.info` says "Jobs are updated every hour". Cloudflare serves cached copies up to about an hour old. The header shows `X-RateLimit-Limit: 50` with no documented window. Rate headers are cached with the body, so they are useless for tracking budget.
- **Terms.** [ToS](https://www.arbeitnow.com/terms) section 11 says "as is", requires a link back to Arbeitnow.com, and allows access to be revoked at any time. Section 2 is a generic personal, non-commercial, no-mirroring license and does not say whether it binds API users. `meta.terms` says "please do not abuse".
- **Coverage.** About 4,000 to 4,700 listings in a rolling window of about 7 days: about 1,950 DE, 1,015 UK, 770 FR and 100 to 450 each for CH and NL. That works out to roughly 280 new DE listings a day. They are mostly tech and corporate roles imported from ATSs. About 9% are remote. All derived from sampled pages.

### Not verified

- The rate-limit window and how the API behaves on a 429.
- Exact totals for .ch and .nl, and the full-walk size. Pages 3 to 9 and some later pages were not fetched.
- Whether ToS section 11 overrides section 2's non-commercial license for API users.
- Whether the feed always holds about 7 days, and whether arbeitnow.com carries non-German EU jobs.
- Whether the separate arbeitnow.co.uk endpoint adds anything the merged feed lacks.
