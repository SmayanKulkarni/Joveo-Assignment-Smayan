# Glassdoor Real-Time (RapidAPI): research notes

Researched 2026-11-02 for [ticket 05](../issues/05-research-glassdoor-real-time.md). Docs only, no API key, no live call.

## Sources

- Listing page: <https://rapidapi.com/things4u-api4upro/api/glassdoor-real-time>. The page is client-rendered. Everything below under "What the listing says" comes from the JSON the page embeds in its server HTML (the `getApiBySlug` and `getApiVersion` query data), fetched 2026-11-02 (page data timestamp 2026-11-01 20:10 UTC).
- Pricing tab: <https://rapidapi.com/things4u-api4upro/api/glassdoor-real-time/pricing>. Same embedded plan data.
- Playground: <https://rapidapi.com/things4u-api4upro/api/glassdoor-real-time/playground>. Per-endpoint parameters and example responses are loaded by the browser after sign-in and are not in the server HTML. Pulling them from RapidAPI's internal API was blocked, so **no parameter or response shape is confirmed here**.
- RapidAPI terms: <https://rapidapi.com/terms> (linked from the hub config as the publish terms).

## What the listing says

| Field | Value |
|---|---|
| Title | Glassdoor Real-Time |
| Description | "Real-time data, unofficial API glassdoor.com, search for jobs, explore company reviews, and analyze salary insights for better career decisions." |
| Provider | Team `api4uPro` (slug `things4u-api4upro`) under organization `things4u` |
| Host | `glassdoor-real-time.p.rapidapi.com` |
| Category | Jobs |
| Created | 2024-12-18 (v1, the only version) |
| Last updated | 2025-10-04 |
| Long description / readme | empty |
| Provider terms of service | none (`termsOfService: null`) |
| Provider website | none (`websiteUrl: ""`) |
| Tutorials | none |
| Hub score | avg latency 1028 ms, service level 100, success rate 100, popularity 9.9 |
| User rating | 3.3 of 5 from 16 votes |

"Unofficial" is the provider's own word. Glassdoor does not offer a public API, so this is a scraper of glassdoor.com resold through RapidAPI.

## Endpoints

26 endpoints, all `GET`, in four groups. Each endpoint's description just repeats its name, so the listing documents nothing about parameters, units or semantics.

| Group | Routes |
|---|---|
| Salaries (6) | `/salaries/auto-complete`, `/salaries/location`, `/salaries/filters`, `/salaries/search`, `/salaries/report`, `/salaries/details` |
| Jobs (4) | `/jobs/auto-complete`, `/jobs/location`, `/jobs/search`, `/jobs/details` |
| Companies (14) | `/companies/auto-complete`, `/companies/search`, `/companies/base-info`, `/companies/overview`, `/companies/overview-details`, `/companies/locations`, `/companies/photos`, `/companies/awards`, `/companies/reviews`, `/companies/benefits`, `/companies/jobs`, `/companies/jobs-details`, `/companies/interviews`, `/companies/interview-details` |
| Conversations (2) | `/conversations/search`, `/conversations/details` |

The order (the listing's own `index`) hints at the call chain, though this is inference from names only:

- Salaries: `auto-complete` (job title to an ID) and `location` (place to a location ID), then `filters`, then `search` (title plus location), then `report` and `details` for one title or employer.
- Jobs: `auto-complete` and `location` resolve IDs, `search` lists postings, `details` fetches one posting.
- Companies: `auto-complete` and `search` find an employer ID, everything else takes that ID.

So one salary figure for "title in city" likely costs 3 to 4 requests (title lookup, location lookup, search, maybe details), and one page of postings costs 3 (two lookups and a search) plus one `jobs/details` per posting if `search` doesn't carry the description. Lookups can be cached per title and city.

## Cost and quota

"A call to any endpoint is one request." Every public plan has a hard monthly limit and no overage price, so calls past the quota are refused rather than billed.

| Plan | Price / month | Requests / month | Rate limit |
|---|---|---|---|
| BASIC | free | 200 (hard) | not enforced in config (250 per minute listed, `enabled: false`) |
| PRO | 15 | 15,000 (hard) | 5 per second |
| ULTRA | 35 | 50,000 (hard) | 5 per second |
| MEGA | 100 | 200,000 (hard) | 5 per second |

Prices carry `currency: null` in the data. RapidAPI bills in USD, so read them as USD. There is also a private `CUSTOM-5000` plan (USD 5, 5,000 requests, overage 0.0005 per request) visible to one developer only, which doesn't apply to us.

The hub config also defines a RapidAPI-wide "Bandwidth Platform Fee": 10,240 MB free, then 0.001 per MB. Whether it is charged on this API's plans is not shown.

At 3 to 4 requests per salary figure, the free tier covers roughly 50 to 65 salary lookups a month. That is enough to probe shapes, not to back a Brief per Run.

## What kind of salary data it is

The listing says nothing about this, so this part rests on how glassdoor.com itself works and is marked unverified in the ticket.

- Glassdoor salary figures are modelled from employee-submitted reports. Its Local Pay Reports methodology (dated 2016-12-29) says Glassdoor applies "a proprietary machine-learning statistical model to millions of individual salary reports submitted anonymously to Glassdoor", and reports "median base pay" for "full-time U.S. workers". It gives no minimum sample size and no percentiles ([methodology](https://api.glassdoor.com/blog/glassdoor-local-pay-reports-methodology/)). The method may have changed since.
- A search snippet of a Glassdoor employer blog post said job listing estimates use "salary data from millions of employees and third-party sources". The URL now serves a marketing page, so that wording is unconfirmed.
- On a glassdoor.com salary page the headline is usually "estimated total pay" split into base pay and additional pay, with a likely range and a count of submitted salaries. If `salaries/search` and `salaries/details` mirror that page, expect per-title-and-location figures with a range (percentiles), a pay period (annual or hourly), a currency matching the Glassdoor country site, and a sample count. None of this is confirmed for this API.
- On glassdoor.com job listings, pay is labeled either as employer-provided or as a Glassdoor estimate. If `jobs/search` keeps that label, it maps cleanly onto Advertised pay versus Estimated pay. If it drops it, every job salary from this source has to be treated as Estimated pay.

In the project's terms this data is neither Advertised pay nor Estimated pay as GLOSSARY.md defines them. Salary endpoint figures describe what people in a title report earning (modelled), not what one Posting offers, so they are a third kind of figure and must not enter `Posting.salary` or any Stat whose Evidence is a set of posting keys.

## Mapping jobs/search to Posting (unconfirmed)

Without a response shape only the obvious targets can be named:

| Posting field | Likely source |
|---|---|
| `source` | new `Source.glassdoor` value |
| `source_id` | Glassdoor job listing ID |
| `title`, `company`, `location` | listing header fields |
| `posted_at` | listing age or date, possibly relative ("3d") |
| `closes_at` | probably none |
| `description` | probably only from `jobs/details`, one extra call per posting |
| `url` | glassdoor.com job URL |
| `salary` | pay range plus period and currency; `predicted` must come from Glassdoor's employer-provided vs estimate label |
| `region`, `domain` | no clear source |

Overlap: Glassdoor (and Indeed, its sister company) aggregate many of the same employer postings that Adzuna and JSearch return, so expect heavy duplication across sources. Not measured.

## Terms

- The provider publishes no terms of service. Only RapidAPI's general terms apply to the subscription.
- Nothing on the listing addresses storing results or attribution.
- Glassdoor's own Terms of Use govern glassdoor.com content. The provider calls this API unofficial, so Glassdoor has not licensed the data to it. Storing or republishing Glassdoor salaries or reviews in a Brief carries that risk. Glassdoor's terms were not read for this note.
