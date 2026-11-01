# Research: Arbeitnow job board API

Type: research
Status: open
Assignee: none
Blocked by: none

## Question

What does the Arbeitnow job board API offer, and how would it map onto a `Posting` and a `Fetch`?

- Endpoints, auth (if any), pagination, page size, rate limits and terms of use, including attribution and caching.
- Which `Fetch` fields it can honour: title search, country, location, radius, date range, category. If it has no server-side search, how many pages a client would need to filter locally, and how fresh the feed is.
- Coverage: countries (it looks Germany and Europe focused), remote jobs, and volume per day.
- Field mapping to `Posting` (`kernel/types.py`): `source_id`, company, location and `region`, `domain` (from tags?), `posted_at`, `closes_at`, description (HTML?), URL, salary (any at all, Advertised or not).
- A live call from a throwaway script outside the repo, if it needs no key, recording one real response shape.

Capture findings in this ticket's Answer, with long notes in `../assets/`.
