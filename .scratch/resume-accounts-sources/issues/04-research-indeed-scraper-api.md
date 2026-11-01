# Research: Indeed Scraper API on RapidAPI

Type: research
Status: open
Assignee: none
Blocked by: none

## Question

What does the Indeed Scraper API (border-line, on RapidAPI: <https://rapidapi.com/border-line-border-line-default/api/indeed-scraper-api>) offer, and can its "create a task and wait for results" model fit a Collection tool call?

- The task model: create task, poll or wait, fetch results. Typical and worst-case time to results, and whether a synchronous "wait" endpoint holds the HTTP call open (and for how long).
- Parameters (query, location, country or Indeed domain, radius, date posted, job type, page or max results) and how they map onto `Fetch`.
- Field mapping to `Posting`, including salary (Indeed's own estimate or Advertised) and a stable `source_id`.
- Quota, price and how a task is counted. Error and timeout behaviour.
- Terms: it scrapes a site whose terms forbid scraping. Record what the listing says, so [Which job sources join the gateway](10-which-job-sources-join-the-gateway.md) can weigh it.

Docs and playground are enough. A live call needs the key from [Subscribe to the job APIs and add keys](09-subscribe-to-the-job-apis.md). Capture findings in this ticket's Answer, with long notes in `../assets/`.
