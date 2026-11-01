# Research: Fantastic Jobs APIs (Active Jobs DB and LinkedIn Job Search API)

Type: research
Status: open
Assignee: none
Blocked by: none

## Question

What do Fantastic Jobs' two APIs offer, and how do the RapidAPI listings compare with buying direct?

- Active Jobs DB (<https://rapidapi.com/fantastic-jobs-fantastic-jobs-default/api/active-jobs-db>) and LinkedIn Job Search API (<https://rapidapi.com/fantastic-jobs-fantastic-jobs-default/api/linkedin-job-search-api>): endpoints (for example the 1h, 24h and 7d windows), filters (title, location, description, organisation, remote, date), page size and offset, and how they map onto `Fetch`.
- The direct developer portal (<https://developer.fantastic.jobs>): is it the same data under a different plan, and is its free tier or pricing better than RapidAPI's? The user's subscription page there needs their login, so judge from the public docs.
- Where the data comes from (ATS career sites; LinkedIn), how much the two overlap with each other and with Adzuna, and whether a `source_id` stays stable.
- Field mapping to `Posting`, including salary (Advertised or estimated), the location hierarchy for `region`, and any domain or category.
- Quota and price per tier, how quota is counted (per call or per job returned), and the terms on storing and caching results. Note anything about LinkedIn data that limits reuse.

Docs and playgrounds are enough. A live call needs the key from [Subscribe to the job APIs and add keys](09-subscribe-to-the-job-apis.md). Capture findings in this ticket's Answer, with long notes in `../assets/`.
