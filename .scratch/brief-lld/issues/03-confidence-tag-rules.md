# Confidence Tag rules

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 02

## Question

How is an Insight tagged High, Medium or Low: computed by code, set by the LLM, or an LLM tag capped by code? What thresholds apply, and how do they answer the spec's "you set and justify the thresholds"? How do Caveats, Sample size, and estimated or snippet-based Evidence affect the tag?

## Answer

Decided by grilling. **Code computes the tag in `render`,** and the LLM has no field for it. The probe's writer didn't adjust to thin evidence, and a rule is what lets the thresholds be stated and justified.

**Each cited Stat is rated on its own Evidence:**

| Rating | Postings | Distinct employers |
|---|---|---|
| High | 30 or more | 10 or more |
| Medium | 10 or more | 5 or more |
| Low | anything else | |

- **Employers** use the grouping in `stats`, and a Posting with no company counts as its own employer. `competition.employer.*` Stats are exempt from the employer minimum, since they cover one employer by construction.
- **Counts are absolute,** not shares of the Sample: the spec says "many postings", and 8 of 8 is still thin. Sample size therefore needs no rule of its own. A Run at the minimum target of 20 Postings can't produce a High.

**The Insight takes the lowest rating among its cited Stats,** because it's only as strong as its thinnest figure. Evidence stays the union (see [The Market Brief schema](02-brief-schema.md)), so citing `demand.sample_size` beside a 6-Posting skill can't inflate the tag. A broad Insight citing many Stats tags low, and the prompt can nudge the writer to split it.

**Three things then cap it at Medium,** worked out from the same facts that raise the Caveats, never by matching Caveat text:

1. It cites `comp.estimated.*`, which is Adzuna's guess.
2. It cites `skills.*` and any Adzuna Posting is in the Sample, since 500-character snippets are partial evidence.
3. The Old data Caveat fired, which applies to every Stat.

Other Caveats only appear in the Run Notes: Too few Postings (the counts show it), Mostly federal (federal pay is kept apart), Pay converted (a small effect) and Pay period assumed (held on the live Run for us and gb).

**Why these numbers:** 30 is a common rule of thumb for when a median stops moving much with each new Posting. Below 10, quartiles and shares move a lot with each Posting. The employer minimums stop one company's repeated ads counting as a market pattern, which is what "consistent" means here: the AI skill has 13 Postings from 4 employers (Low), and SQL has 14 from 12 (Medium). Pay spread was rejected as a second rule covering one Dimension. These numbers are judgement checked against one role's fixture, not tuned across roles.

**Checked on the 125 fixture Postings** (real `stats` code, 2026-10-31, shown as Postings/employers):

| Result | Stats |
|---|---|
| High | `competition.direct_share` 68/42, `titles.variant.data-engineer` 35/19, `comp.disclosed_share` 100/49 |
| Medium, by count | `comp.federal.median` 25/12, `skills.sql.count` 14/12, `skills.python.count` 18/17, Booz Allen's employer count 23/1 (exempt) |
| Medium, capped from High | `comp.estimated.median` 100/49 |
| Low | `skills.artificial-intelligence.count` 13/4, `skills.pyspark.count` 8/8, `comp.estimated.lead.median` 5/5 |

In practice, a Run with only estimated pay never gets a High pay Insight, and an Adzuna Run never gets a High skills Insight.

**`Insight` gains `confidence_reason: str`, written by code** and absent from `BriefDraft`, such as "Medium: weakest cited Stat has 18 Postings from 17 employers; skills come from snippets". Without it, Evidence of 125 Postings beside a Low tag would go unexplained.

**The rationale lives in `docs/lld/brief.md`,** and the Markdown Brief carries a two or three line key stating the rule. `brief.json` has no key, since `confidence_reason` explains each tag there.

**Only Insights are tagged.** Client Recommendations and the Hiring Outlook stay untagged, as the spec and schema have them.

Left to later tickets:

- [Client recommendations](05-client-recommendations.md): with no tag, a salary band's `reason` has to say when pay is estimated.
- [Brief prompts](11-prompts.md): whether the writer is told this rule, so it phrases claims to match and splits broad Insights.
- [Render and Run Notes](10-render-and-run-notes.md): places the key in the Markdown.
- [Write the Brief LLD doc](12-write-brief-lld-doc.md): Analysis §14 expects a recommendation's pay to use "`estimated` at a lower tag", which no longer holds, so it needs correcting in the upstream sweep.
