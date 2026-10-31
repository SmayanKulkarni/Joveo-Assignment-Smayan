# Live check of the draft design

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01

## Question

Added while resolving the open tickets. The first probe tested a schema that no longer exists. Do the narrower draft, a figure check, the critic and the Outlook rule hold up on real Stats?

This gathers facts and is not kept. It spends no Adzuna quota.

## Answer

Run on 2026-10-31 with `minimax/minimax-m3.1-flash` and `typesafe/jev-1.14`, using real Analysis over the 125 fixture Postings and slices of them. Cost wasn't measured, and is in cents.

### Round 1: a strict design failed

Validator on figures per cited Stat, and on every Dimension having an Insight, with one model and so 2 attempts. Over two sets of 4 runs, 7 of 8 ended in `LLMExhausted(bad_output=True)`. In the set where causes were printed:

| Run | Result |
|---|---|
| Full, 125 | Whitespace runaway, 7,315 lines at 4,096 tokens. **The first probe saw this only at zero Postings, so it isn't limited to them** |
| Full, 125 | Passed, but wrote "125.0 postings" and "139989.0 USD/year" |
| 50, with focus | Left demand and skills uncovered, even after the error was fed back |
| Thin, 8 | A figure from an uncited Stat, even after the error was fed back |

The one that passed also showed the critic churning: a whole-draft revision rewrote accurate Insights and their scores fell, such as "The sample contains 125.0 postings" from 0.95 to 0.20. The Summary scored 0.14 and 0.15, so it would force every Run to the cap.

### Round 2: the design adopted

Figures checked against any Stat, the Caveats and the request. No coverage check. Values shown with no `.0`. Critic judges Insights only, with Caveats in its state. A revision replaces only the flagged Insights. 8 runs: 4 of 125, 2 of 50 with focus, 2 of 8.

| Measure | Result |
|---|---|
| Drafts valid | 8 of 8, with no runaway |
| Time | 2 to 11 s |
| Insights | 8 on full runs, 3 at the thin cap |
| Critic passes first time | 51 of 54 |
| Flagged Insights replaced and then passing | 2 of 3 |
| Request size | 0.8 to 1.9 KB per Insight |
| Runs leaving a Dimension uncovered | 4 of the 6 non-thin runs, each missing `titles_seniority` |

The flags were mostly right. Two were real faults: a ranking of skills that named machine learning without citing it (0.08), and "largest employer" citing only that employer (0.22). The third was similar: "leads the sample" on two cited Stats (0.46), then 0.27 after revision, so it ships unconfirmed.

**Wrong and not caught:** the writer read Analysis's Caveat "no advertised pay reached 5 figures" as a money amount, and wrote "none of the 100 postings reached five figures". The critic passed it at 0.89. The wording of that Caveat is the fix.

**The default outlook leaks.** Told "competitive" on 8 Postings, the writer called the market competitive. So a default outlook mustn't reach the writer.

### The Outlook rule on the fixtures

The fixtures have no fetch records, so the newest posted date stood in for "now".

| Sample | Employers | Trend | Median years | Senior and up | Result |
|---|---|---|---|---|---|
| All, 125 | 61 | rising | 4 | 26% | Competitive |
| Adzuna, 100 | 49 | rising | 5 | 29% | Hard to fill |
| Adzuna, 50 | 19 | rising | none | 28% | Competitive |
| Federal, 25 | 12 | none | 1 | 16% | Competitive |
| Adzuna, 8 | | | | | Competitive, by default |

The result turns on one median year between the first two rows. No fixture reaches Favourable, so only unit tests can exercise it.

### Recommendations on the fixtures

Title by employers: Data Engineer (35 Postings, 19 employers), then Senior Data Engineer (14, 11). "Data Engineer III" (3, 1) and "Data Engineer 4" (3, 1) fall to the two-employer minimum. Top skills include real tools and a few phrases such as "data ingestion". Pay bands exist for `estimated` overall, its `senior` and `lead` slices, and `federal`.

### Limits

One role, a few runs, one model rather than the two-model chain, and federal pay wasn't written on its own. Treat these as direction, and the live smoke in the LLD as the real test.
