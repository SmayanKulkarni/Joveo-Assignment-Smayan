# Which job sources join the gateway

Type: grilling
Status: open
Assignee: none
Blocked by: [Research: Arbeitnow job board API](01-research-arbeitnow.md), [Research: JSearch on RapidAPI](02-research-jsearch.md), [Research: Fantastic Jobs APIs](03-research-fantastic-jobs-apis.md), [Research: Indeed Scraper API](04-research-indeed-scraper-api.md), [Research: Glassdoor Real-Time](05-research-glassdoor-real-time.md), [Subscribe to the job APIs and add keys](09-subscribe-to-the-job-apis.md)

## Question

Which of Arbeitnow, JSearch, Active Jobs DB, LinkedIn Job Search API, Indeed Scraper API and Glassdoor Real-Time become a `Source`, and with what role and limits?

- For each one: in, out, or salary-only. Weigh coverage beyond Adzuna, Duplicates against Adzuna, data quality (descriptions, salary, location), quota and price, latency (Indeed's task model), and terms (scraping, LinkedIn, caching).
- Arbeitnow is in, because the user asked for it. Decide only what it's for: which countries and which kinds of role.
- For each source: the daily or monthly budget guard (like Adzuna's 250 a day), whether it's cached in L1 and L2, and what happens to a Run when it's down or out of quota.
- Whether the direct Fantastic Jobs portal replaces its RapidAPI listings.
- The attribution each source needs on screen and in `brief.md` (see `ATTRIBUTION` in `gateway/types.py`).

A source that gets ruled out gets one line in the map's Out of scope.
