# Sufficiency, broaden and blocked Attempts

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

When is the Sample enough, what can `broaden` change, how many Attempts are allowed, and what happens when an Attempt can't get more data at all?

## Answer

Decided by grilling.

- **Sufficiency:** `len(sample) >= current_plan.target_postings`. There is no separate noise rule, since noise already shows up as too few Relevant Postings.
- **USAJOBS counts** toward the target the same as Adzuna. They're real open jobs, and filtering them would discard the only Evidence some roles have. A Caveat fires when they dominate ([Caveats](06-caveats.md)).
- **2 broadens, so 3 Attempts,** before `low_data_review`. Attempts left = 2 − `len(broadened_plans)`.
- **`broaden` runs on the strong tier and fills a whole `SearchPlan`,** given the current plan, counts per title and a few example titles `relevance` rejected.
  - Code pins `country` and `target_postings`, so the model can't reach Sufficiency by lowering the target or leave the market the user asked about.
  - Its prompt offers the moves: more title variants, a wider radius, an older `max_days_old`, dropping `category`, a country-wide search, and replacing a noisy title. The last covers the spec's "broaden or refine".
  - `fetch_agent` can still page deeper in the new Attempt, since repeated Fetches are free L1 hits.
  - `LLMExhausted` propagates.
- **`fetch_blocked: str | None`.** `relevance` writes the reason when an Attempt can't get more data: Adzuna at 0 calls outside the US, or every Fetch in the Attempt failing. A set value goes straight to `low_data_review`, skipping remaining Attempts.
  - A USAJOBS-backed Run in the US carries on normally.
  - **`gateway.calls_left(source)`** is a new one-line method. `failures` holds plain strings, and when every source fails `fetch` raises with no result, so nothing else carries the signal.
  - The check is skipped when `replay_cache` is set, otherwise a recorded Run could take a different route on replay.
