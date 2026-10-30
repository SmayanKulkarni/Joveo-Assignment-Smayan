# Caveats

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

Gateway §17 and Kernel §9 hand Collection every Caveat's trigger and wording. Which does it raise, when, and from which node?

## Answer

Decided by grilling.

| Caveat | Fires when | Written by |
|---|---|---|
| Postings the mapper dropped | `dropped` > 0, with the count | `collect` |
| One source failed | `failures` has a source and another source answered, or L2 served a partial page | `collect` |
| Mostly federal | over 50% of the Sample is USAJOBS | `relevance` |
| Old data | over half of the Sample is older than 30 days | `relevance` |
| Too few Postings | the user continues below target, or pass 1's pass-through does | `low_data_review` |
| Broadened | any `broaden` ran, with the count and what changed | `relevance`, once Sufficient or at the Pause |
| Jev degraded | any `llm_fallback` or `truncated` verdict, one per Attempt with count and keys | `relevance` |
| Replay age | any `cache == replay`, with the oldest `fetched_at`; live calls during replay reported too | `collect` |

- **No Caveat for a normal L2 read,** because up to 7 days old is within the data's expected freshness.
- **Source `total` is a `note`,** leaving out `cache == store`, and Brief renders it as labelled disclosure.
- Merged Duplicates are a `note`, not a Caveat (Gateway §6).
