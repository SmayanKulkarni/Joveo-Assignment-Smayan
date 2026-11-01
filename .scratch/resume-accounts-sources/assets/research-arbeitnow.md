# Arbeitnow job board API: research notes

Researched 2026-11-02 for [issue 01](../issues/01-research-arbeitnow.md). Live calls were made on 2026-11-01 around 20:10 UTC from a throwaway script outside the repo.

## Sources

- Blog post that announces the API: <https://www.arbeitnow.com/blog/job-board-api>
- Postman documentation, published 2021-11-27: <https://documenter.getpostman.com/view/18545278/UVJbJdKh> (raw collection JSON: `https://documenter.gw.postman.com/api/collections/18545278/UVJbJdKh?segregateAuth=true&versionTag=latest`)
- Terms of service: <https://www.arbeitnow.com/terms> (sections 2 "Use License" and 11 "API"; the page has no last-updated date)
- The live endpoint itself: <https://www.arbeitnow.com/api/job-board-api>. Its `meta.terms` and `meta.info` strings are first-party statements.

## Endpoint and auth

- One endpoint: `GET https://www.arbeitnow.com/api/job-board-api`. The blog also lists `https://www.arbeitnow.co.uk/api/job-board-api` for the UK, but the main endpoint already includes .co.uk jobs (see Pagination).
- No key and no auth. The blog says it "requires no API key". The live call needed no headers.
- `Access-Control-Allow-Origin: *`, so a browser could call it directly too.
- The blog mentions a paid "private, custom API endpoint" on request (contact@arbeitnow.com). There are no public details.

## Response shape (live)

Top level: `{"data": [...], "links": {...}, "meta": {...}}`.

```json
"links": {"first": "https://www.arbeitnow.com/api/job-board-api?page=1", "last": null, "prev": null,
          "next": "https://www.arbeitnow.com/api/job-board-api?page=2"},
"meta": {"current_page": 1, "current_page_url": "...?page=1", "from": 1,
         "path": "https://www.arbeitnow.com/api/job-board-api", "per_page": 300, "to": 300,
         "terms": "This is a free public API for jobs, please do not abuse. I would appreciate linking back to the site. By using the API, you agree to the terms of service present on Arbeitnow.com",
         "info": "Jobs are updated every hour and order by the `created_at` timestamp. Use `?page=` to paginate. Read more information here: https://www.arbeitnow.com/blog/job-board-api"}
```

One item from page 1, with the description cut short:

```json
{
  "slug": "manager-applied-ai-engineering-codex-munich-421206",
  "company_name": "OpenAI",
  "title": "Manager, Applied AI Engineering (Codex)",
  "description": "<h3><strong>About the Team</strong></h3><p style=\"min-height:1.5em\">The Applied AI Engineering team ...",
  "remote": false,
  "url": "https://www.arbeitnow.com/jobs/companies/openai/manager-applied-ai-engineering-codex-munich-421206",
  "tags": ["Go To Market"],
  "job_types": ["Full Time"],
  "location": "Munich, Germany",
  "created_at": 1793558417
}
```

All 1,545 distinct items seen had exactly these 10 keys. The 2021 Postman sample has the same 10 keys, so the schema has stayed the same for about five years.

- `created_at` is an integer Unix timestamp in seconds.
- `description` is HTML in every item (353 to 55,502 characters).
- `tags` and `job_types` are free-text lists from each employer's ATS. They mix languages and formats ("Full Time", "Unbefristeter arbeitsvertrag", "fulltime permanent", "13001 - Engineering", "THG Beauty"). 55 items had no tags.
- `location` is a free-text string. 63 of 1,545 were blank. Formats vary: "Berlin", "Berlin, Berlin", "Utrecht, Utrecht, Nederland", "Paris Office", "Remote job".
- There is no salary field, no closing date, no country field, no category, no numeric id and no lat/long.

## Pagination (observed, mostly undocumented)

- `?page=N`, 1-based. `links.last` is always null and there is no total count, so a client walks until `data` is empty.
- Each page **merges five country sites**. Item `url` hosts show this, consistent across every page:
  - up to 100 from `www.arbeitnow.com` (Germany),
  - up to 50 each from `www.arbeitnow.co.uk`, `.fr`, `.ch` and `.nl`.
  So page 1 has 300 items. Pages shrink as the smaller sites run out: .ch and .nl were gone by page 10, .fr ended on page 16 (22 items), .com on page 20 (51), .co.uk on page 21 (15). Pages 22 and later returned `data: []`.
- `meta.per_page`, `from` and `to` are unreliable. `from` steps by 100 (the .com paginator: page 2 has `from: 101`) while `to` echoes the item count. The 2021 Postman sample shows `per_page: 100` from before the other sites were merged in.
- Consecutive pages lined up per site. Page 2's first .com item was page 1's 100th item, which is a one-item shift between two cached copies.
- Ordering is roughly, not strictly, by `created_at` descending: page 1 had 8 inversions, and page 20 still held items created on 2026-11-01. A client cannot stop at a date cutoff. It has to walk every page.
- Size: page 1 is 2.4 MB of JSON, page 10 is 1.7 MB and page 20 is 0.7 MB. A full walk is about 21 requests and roughly 30 to 40 MB uncompressed (estimated; pages 3 to 9 were not fetched).

## Filters

Only `visa_sponsorship` is documented (blog). Tested live:

| Param | Effect |
| --- | --- |
| `visa_sponsorship=true` | Honoured. 295 items, different set, date span back to 2026-10-26. |
| `search=engineer` | Ignored. Same items as an unfiltered page 1. |
| `location=berlin` | Ignored. |
| `remote=true` | Ignored. Still 286 non-remote items out of 300. |
| `tags=Engineering` | Ignored. |

The blog suggests filtering on the `remote` field client-side, so ignoring these params is expected. There is no server-side title, location, radius, date or category search, and no country selector. The five sites always come back together.

## Rate limits and caching

- Live headers: `X-RateLimit-Limit: 50`, `X-RateLimit-Remaining: 48`. The window is not documented. In 2021 the limit was 3 (Postman sample).
- Responses come through Cloudflare with `cf-cache-status: HIT` and `Age` up to about 3,400 s. The rate-limit headers are cached with the body, so `Remaining` stayed at 49 across every call and cannot be used to track budget.
- `Cache-Control: private, max-age=432000` (5 days), but `meta.info` says jobs update every hour. In practice, data is up to about an hour behind the origin.
- No 429 was seen in 19 calls.

## Terms

- `meta.terms`: "free public API for jobs, please do not abuse. I would appreciate linking back to the site."
- ToS section 11 (API): provided "as is" and "as available" with no warranty. Users "agree to providing a link back to Arbeitnow.com on your platform". Access can be revoked at any time.
- ToS section 2 (Use License) is the generic site license: "personal, non-commercial transitory viewing only". It bars copying, commercial use and public display, and "mirror[ing] the materials on any other server". It also says downloaded materials must be destroyed when the license ends. It does not say whether section 11 overrides it for API users. That is a real ambiguity for a deployed, public tool.
- Nothing addresses caching duration or scraping. The `Store` cache of raw responses is not forbidden, but section 2's anti-mirroring clause argues for short retention and no re-publication of full descriptions.

## Coverage and volume

Distinct items seen across 8 distinct pages (1, 2, 10, 11, 13, 16, 20, 21) plus fresh copies of page 1:

| Site | Seen | Feed total (derived from page counts) | Top locations | Remote |
| --- | --- | --- | --- | --- |
| arbeitnow.com (DE) | 708 | 1,951 | Berlin, Munich, Hamburg, Cologne | 87 |
| arbeitnow.co.uk | 365 | 1,015 | London, Manchester | 36 |
| arbeitnow.fr | 272 | 772 | Paris, Toulouse | 3 |
| arbeitnow.ch | 100 | 100 to 450 | Zurich, Lausanne, Nyon | 8 |
| arbeitnow.nl | 100 | 100 to 450 | Amsterdam, Veenendaal, Delft | 8 |

- The whole feed is about 4,000 to 4,700 listings and covers roughly the last 7 days (oldest seen: 2026-10-25). It is a rolling window, not an archive.
- Implied volume: about 280 new listings a day on .com, 145 on .co.uk and 110 on .fr. This is the feed window divided by 7 days, not a measured daily count.
- Skewed to tech, startups and corporate roles imported from ATSs (Greenhouse, SmartRecruiters, Join.com, Teamtailor, Recruitee, Comeet, per the blog). 458 of 1,545 titles carry German gender markers such as "(m/w/d)".
- `remote` was true for 142 of 1,545 (9%). The `remote` flag, "Remote job" locations and the "Remote" tag do not always agree.

## Mapping to `Posting`

| `Posting` field | From | Notes |
| --- | --- | --- |
| `source` | new `Source.arbeitnow` | Also add an `ATTRIBUTION` entry with a link to arbeitnow.com. |
| `source_id` | `slug` | Unique across all 1,545 seen. The numeric tail looks like a site-local id, so it is unsafe on its own across the five sites. |
| `title` | `title` | Collapse whitespace. |
| `company` | `company_name` | Never blank in the sample. |
| `location` | `location`, falling back to the site's country name when blank | 4% blank. |
| `region` | country from the `url` host (`.com` gives DE, `.co.uk` GB, and so on), plus the city from `location` | There is no structured area list like Adzuna's `location.area`. |
| `domain` | `None`, or a small keyword map from `tags` | Tags are free text and do not line up with `ADZUNA_CATEGORIES`. |
| `posted_at` | `created_at`, read as a UTC date | `datetime.fromtimestamp(ts, UTC).date()`. |
| `closes_at` | `None` | Not in the feed. |
| `description` | `description` with HTML stripped | stdlib `html.parser` is enough. The repo has no HTML stripper yet. |
| `url` | `url` | An arbeitnow.com/.co.uk/... job page, not the ATS page. No tracking params. |
| `salary` | `None` | No salary field. Arbeitnow runs a "jobs with salary" page on its site, but the API exposes none of that. Some descriptions mention pay in prose (a loose regex matched 455 of 1,545), but parsing prose is out of scope. |

## Mapping to `Fetch`

| `Fetch` field | Honoured? | How |
| --- | --- | --- |
| `title` | Local only | Match on `title` after fetching the whole feed. |
| `country` | Local only | Keep items whose `url` host matches: de to `.com`, gb to `.co.uk`, fr to `.fr`, ch to `.ch`, nl to `.nl`. All five codes are already in `ADZUNA_CURRENCY`, so `Fetch` validation passes. Any other country gets no results. |
| `location` | Local, weak | Substring match on the free-text `location`. |
| `radius_km` | No | There are no coordinates. |
| `max_days_old` | Local, capped near 7 | Filter on `created_at`. The feed only holds about 7 days, so the 60-day maximum cannot be met. |
| `category` | No | There is no category field. |
| `page` | No direct meaning | API pages mix five countries and have no relevance order. |

Because no filter runs server-side, every `Fetch` needs the full feed. The sensible client walks all pages once (about 21 calls, about 35 MB), caches that snapshot for about an hour (the feed's own refresh rate), and answers each `Fetch` by filtering it locally. `Page.total` is then the local match count, and `Fetch.page > 1` returns an empty page.

## Method

- Scripts in `C:\Users\SMAYAN~1\AppData\Local\Temp\claude\D--Joveo\ac31a377-0f8c-4ddc-9d79-1e3775ebee11\scratchpad\arbeitnow\` (curl plus small Python summaries). Nothing ran inside the repo.
- 19 GET calls: page 1; pages 2, 10, 11, 13, 16, 20 to 25, 30 and 40; and page 1 with each of the five filter params.

## Not verified

- The rate-limit window (per minute or per hour), and what happens on a 429.
- Pages 3 to 9, 12, 14, 15 and 17 to 19 were not fetched, so the totals for .ch and .nl, the full-walk size and the exact ordering are derived, not counted.
- Whether ToS section 11 overrides section 2's non-commercial, no-public-display license for API users. Only Arbeitnow can answer that.
- Whether `.com` holds non-German EU jobs beyond the few seen (it is labelled "Europe" on the blog).
- Whether the feed window is always about 7 days, or that was just this week.
- Whether the separate arbeitnow.co.uk endpoint returns anything the merged endpoint does not.
