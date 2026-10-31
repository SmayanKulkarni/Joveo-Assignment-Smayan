# Caveats and the run log

Type: grilling (delegated to the agent)
Status: resolved
Assignee: smayankulkarni05
Blocked by: 04, 05, 06, 07

## Question

Which limitations found in Analysis become Caveats (Kernel §9), and who writes them, given that `batch_extract` branches can't log?

## Answer

| Caveat | Fires when | Written by |
|---|---|---|
| Postings not extracted | Any Sample key has no Extraction, with the count | `stats` |
| Skills merged by spelling only | `normalise_skills` hit bad output | `normalise_skills` |
| Skills from snippets | Any Adzuna Posting in the Sample, with the count. Their 500-character snippets undercount skills | `stats` |
| Pay is estimated | No `advertised` Stats, but `estimated` Stats exist | `stats` |
| Too little pay data | No group reached 5 figures | `stats` |
| Pay period assumed | Any `advertised` figure had an `unknown` period, with the count | `stats` |
| Implausible pay excluded | Any figure was excluded, with the count | `stats` |
| Pay converted | The Stat currency differs from a Posting's, with the rate date | `stats` |
| Currency unavailable | The requested currency isn't in the table | `stats` |

**Federal pay kept apart isn't a Caveat.** The Stats are labelled, and it's by design. Collection's "Mostly federal" Caveat covers the tilt.

**Skills not in their Posting are a `note`, not a Caveat.** They were dropped, so what's reported is grounded, and nothing about the Brief is less trustworthy.

**`stats` is the natural writer** because it runs once and sees everything, and it computes all of these from state, so branches record nothing but `ungrounded`.

**Other log entries**

| Node | Writes |
|---|---|
| `normalise_skills` | `note` listing every merge |
| `stats` | one `note`: Sample size, Extractions, Stats produced, skills dropped |

A transient failure stopping the Run isn't a Caveat either (Kernel §9).
