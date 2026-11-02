# Subscribe to the job APIs and add keys

Type: task
Status: out of scope
Assignee: none
Blocked by: none

## Question

The source decision needs live calls, and only the user can sign up. This is done when the keys are in `.env` and the facts below are recorded here.

Checklist for the user (HITL):

1. Sign in to RapidAPI and subscribe to the free (Basic) plan of JSearch, Active Jobs DB, LinkedIn Job Search API, Indeed Scraper API and Glassdoor Real-Time. Skip any whose free plan needs a card, and note it here.
2. Add one line to `.env`: `RAPIDAPI_KEY=...`. One key covers every RapidAPI subscription.
3. If the direct Fantastic Jobs portal gives a separate key or a better free tier, also add `FANTASTIC_JOBS_API_KEY=...`.
4. Record here the free quota per month or per day for each API, and whether overage is billed or blocked. The RapidAPI pricing tab shows both.

The agent then makes one live call per API from a throwaway script outside the repo. It records the real response shape and latency, and never pastes a key or a full URL.

## Out of scope

Closed 2026-11-02: the user dropped every RapidAPI source and kept only Arbeitnow. Arbeitnow is keyless, so there is nothing to subscribe to.
