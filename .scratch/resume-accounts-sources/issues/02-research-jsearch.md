# Research: JSearch on RapidAPI

Type: research
Status: open
Assignee: none
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
