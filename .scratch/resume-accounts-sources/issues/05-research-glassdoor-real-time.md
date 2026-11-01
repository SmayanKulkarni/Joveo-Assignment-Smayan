# Research: Glassdoor Real-Time on RapidAPI

Type: research
Status: open
Assignee: none
Blocked by: none

## Question

What does Glassdoor Real-Time (things4u, on RapidAPI: <https://rapidapi.com/things4u-api4upro/api/glassdoor-real-time>) offer, and is it a postings source, a salary source, or both?

- Endpoints: salaries auto-complete, salary estimates by title and location, company search and reviews, and any job search. For each: the parameters, the response shape and what one call costs.
- Salary data: is it reported pay (from employees), an estimate, or advertised? What period, currency, percentiles and sample size does it give? Which countries and cities does it cover?
- If it has job search: the field mapping to `Posting` and the overlap with other sources.
- Quota, price and terms on storing results and attribution.

This feeds [Salary benchmarks in the Brief](13-salary-benchmarks-in-the-brief.md). Docs and playground are enough. A live call needs the key from [Subscribe to the job APIs and add keys](09-subscribe-to-the-job-apis.md). Capture findings in this ticket's Answer, with long notes in `../assets/`.
