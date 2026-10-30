# What Relevant means and how it is judged

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

What makes a Posting Relevant, how is Jev called for it, and what happens to verdicts and Postings across Attempts?

## Answer

Decided by grilling.

- **Role only.** A Posting is Relevant if it's really the researched role, at any seniority and in any location the search returned. Judging seniority too would empty the Sample of unlevelled Postings and bias the seniority mix, which is itself a reported Dimension. For "Senior Data Analyst, Bangalore":
  - "Data Analyst" with no level: Relevant
  - "Data Entry Analyst": not Relevant
  - a FAA "Public Notice" talent pool announcement: not Relevant, because it isn't a job advertisement for the role
- **One `jev.judge` request per Posting.** Batching saves little: 500 Postings cost under a cent at $0.042/M, and a shared request has to fit the 32 KB limit, which USAJOBS descriptions of up to 4,000 characters use up quickly.
- **`relevance_verdicts: dict[str, bool]`.** A new Collection slice, so later Attempts judge only new Postings. This is safe because verdicts judge against `hiring_request`, which doesn't change. `sample` is recomputed from verdicts each Attempt, as Kernel §6 says.
- **The Sample draws on every Attempt,** including Postings a later plan wouldn't have found. Relevance doesn't depend on the plan, so the Posting stays good Evidence, and this avoids spending quota to find it again.
- **No cap when the Sample overshoots the target.** Large Samples are Analysis's batching problem.
