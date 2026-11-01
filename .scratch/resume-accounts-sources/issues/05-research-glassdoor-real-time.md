# Research: Glassdoor Real-Time on RapidAPI

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

What does Glassdoor Real-Time (things4u, on RapidAPI: <https://rapidapi.com/things4u-api4upro/api/glassdoor-real-time>) offer, and is it a postings source, a salary source, or both?

- Endpoints: salaries auto-complete, salary estimates by title and location, company search and reviews, and any job search. For each: the parameters, the response shape and what one call costs.
- Salary data: is it reported pay (from employees), an estimate, or advertised? What period, currency, percentiles and sample size does it give? Which countries and cities does it cover?
- If it has job search: the field mapping to `Posting` and the overlap with other sources.
- Quota, price and terms on storing results and attribution.

This feeds [Salary benchmarks in the Brief](13-salary-benchmarks-in-the-brief.md). Docs and playground are enough. A live call needs the key from [Subscribe to the job APIs and add keys](09-subscribe-to-the-job-apis.md). Capture findings in this ticket's Answer, with long notes in `../assets/`.

## Answer

Researched 2026-11-02. Docs only, no key, no live call. Long notes: [research-glassdoor.md](../assets/research-glassdoor.md).

### Recommendation

- Don't add it as a postings source now. JSearch and Adzuna already cover job search, and this listing documents nothing about its fields.
- Treat it as a salary benchmark candidate only. Its salary figures are reported pay modelled by Glassdoor, a third kind that is neither Advertised pay nor Estimated pay. Never put them in `Posting.salary` or in a Stat whose Evidence is posting keys. Ticket 13 should decide how such a figure is shown.
- Before building, spend part of the free tier (200 requests) on one probe of `salaries/auto-complete`, `salaries/location`, `salaries/search` and `jobs/search` to capture real shapes.
- Weigh the terms risk: the provider calls it "unofficial", publishes no terms, and says nothing on storing or attribution.

### Key findings

- It is both a salary source and a postings source on paper: 26 `GET` endpoints on host `glassdoor-real-time.p.rapidapi.com` in four groups. Salaries (6): `auto-complete`, `location`, `filters`, `search`, `report`, `details`. Jobs (4): `auto-complete`, `location`, `search`, `details`. Companies (14), including `search`, `overview`, `reviews`, `benefits`, `interviews`, `jobs`. Conversations (2). ([listing](https://rapidapi.com/things4u-api4upro/api/glassdoor-real-time))
- Every endpoint's description just repeats its name. There is no readme, no tutorial, no provider website and no provider terms. Parameters and example responses load only in the signed-in playground, so none are confirmed. ([playground](https://rapidapi.com/things4u-api4upro/api/glassdoor-real-time/playground))
- The provider describes it as "Real-time data, unofficial API glassdoor.com". It is run by team api4uPro (org things4u), was created 2024-12-18 and last updated 2025-10-04. Hub score: about 1 s average latency, 100% success. Users rate it 3.3/5 (16 votes).
- One call to any endpoint counts as one request. Plans, all hard monthly limits with no overage: BASIC free 200; PRO USD 15 for 15,000; ULTRA USD 35 for 50,000; MEGA USD 100 for 200,000. Paid plans allow 5 requests per second. ([pricing](https://rapidapi.com/things4u-api4upro/api/glassdoor-real-time/pricing))
- One salary figure likely costs 3 to 4 calls (title lookup, location lookup, search, maybe details). That puts the free tier at about 50 lookups a month.
- Glassdoor's own salary data is a machine-learning model over "millions of individual salary reports submitted anonymously", and its published pay reports give "median base pay" ([Glassdoor methodology, 2016](https://api.glassdoor.com/blog/glassdoor-local-pay-reports-methodology/)). So this API's salary endpoints most likely return employee-reported, modelled pay, not advertised pay. That is inferred from Glassdoor, not stated by the listing.

### Not verified

- Parameters, response fields, pagination and error shapes of every endpoint.
- Whether salary responses carry percentiles, a sample count, base vs total pay, a pay period and a currency, and which countries and cities resolve.
- Whether `jobs/search` keeps Glassdoor's employer-provided vs estimated pay label. Without it, every job salary from this source has to count as Estimated pay.
- Whether `jobs/search` returns full descriptions or needs a `jobs/details` call per posting, and how much it overlaps Adzuna and JSearch.
- Whether RapidAPI's hub-wide bandwidth fee (10,240 MB free, then USD 0.001 per MB) applies to these plans.
- What Glassdoor's own Terms of Use say about scraped data. Not read.
