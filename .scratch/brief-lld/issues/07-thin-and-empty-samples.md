# Thin and empty Samples

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 03, 04, 05

## Question

What does the Market Brief say when a Run continues at `low_data_review` with a weak Sample, or with zero Postings and `MarketStats(sample_size=0, stats=[])`? Does `write_brief` still call the LLM at zero, and does `critic` run? What fills the required parts, such as the outlook and recommendations, when no Evidence exists?

## Answer

Decided by the agent, on the user's instruction.

**Zero Postings: no LLM and no Jev.** The first probe's zero-Posting calls took up to 464 s, ran away, and said favourable about nothing, and there's nothing to say.

| Part | At zero |
|---|---|
| `write_brief` | Writes a code-built draft with no call: "No Relevant Postings were found for {role} in {location}, so this Brief has no market findings." `summary_stat_ids` and `insights` are empty |
| `critic` | Runs as a node, judges nothing and routes to `render`. No special route, because its list of unjudged Insights is empty |
| Insights | `[]`. This resolves the question left by [The Market Brief schema](02-brief-schema.md): the final Brief has no minimum, and the draft's minimum applies only to what the LLM returns |
| Outlook | Competitive, by default, with the reason saying so and `stat_ids=[]` |
| Recommendations | All three `None` |
| Run Notes | Whole, since they matter most here: the plans tried, and Too few Postings and any other Caveats |

**Weak Samples:** the writer runs, with two regimes, because the probe showed it doesn't shrink its output by itself:

| Sample | At most | Every Dimension covered |
|---|---|---|
| 1 to 9 Postings | 3 Insights | No, unless no Insight survives |
| 10 or more | 8 Insights | Yes |

Below 10 Postings, no Stat can rate above Low, and filling all five Dimensions is padding. The cap goes into the input and the check, and 2 thin runs obeyed it.

The rest needs no thin rule, since it already follows from the others: tags from [Confidence Tag rules](03-confidence-tag-rules.md), a default outlook below 20 Postings from [Hiring Outlook rules](04-hiring-outlook-rules.md), and `None` where [Client Recommendations](05-client-recommendations.md) minimums fail.

**One line sits below the Summary in Markdown** when the Sample is under `current_plan.target_postings`: "Weak Sample: 8 Postings against a target of 30. Treat this Brief as directional." It's code, so it holds whatever the writer says, and the Too few Postings Caveat holds the detail in the Run Notes.
