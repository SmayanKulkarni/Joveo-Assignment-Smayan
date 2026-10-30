# Search Plan and its limits

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01

## Question

How does `plan` produce a Search Plan that the Gateway can run within its quota?

- Which fields the LLM fills and which limits apply.
- Where those limits live, given the LLM's output, a user's edit and Collection's `broaden` all produce plans.
- What happens to seniority, work mode and employment type.

## Answer

Decided by grilling, in two steps: the limits first, then where they live.

- **The strong tier fills `SearchPlan` directly.** The model fills every field, so Kernel §3's schema policy allows it, with no separate draft schema.
- **Limits go on the Kernel's `SearchPlan`,** so the LLM's output, an edit at `plan_review` and `broaden` all pass the same checks. A violation from the LLM is fed back on the retry. A violation in an edit is `InvalidAnswer`, which re-prompts. This replaced an earlier choice to put them on a stage-private draft schema.

| Field | Limit | Why |
|---|---|---|
| `titles` | 1–4 | Each title is its own Fetch, and Adzuna allows 25 calls a day |
| `country` | in `ADZUNA_CURRENCY` | `Fetch` rejects anything else |
| `radius_km` | 0–100 | A wider radius stops being one market |
| `max_days_old` | 1–60 | USAJOBS's `DatePosted` caps at 60 |
| `target_postings` | 20–200 | Below 20, a Stat means little. Above 200, Sufficiency can force a broaden on a healthy market. |
| `category` | in `ADZUNA_CATEGORIES`, or null | A tag the source doesn't know would silently find nothing |

- **`ADZUNA_CATEGORIES`** sits in `kernel/types.py` beside the currency table. The tags come from `DOMAINS` in `gateway/usajobs.py`, and a test keeps the two equal. Adzuna's list is per country, so the check is only that a tag is known.
- **Seniority** goes into `titles` only if the user stated it. **Work mode and employment type** can't be searched on, so they stay on `hiring_request` and reach the Run Notes.
- **To verify in the build:** both chain models must accept `maximum` and `maxItems` under strict `json_schema`. If one rejects them, the limits move into a `model_validator`, which leaves them out of the schema.
