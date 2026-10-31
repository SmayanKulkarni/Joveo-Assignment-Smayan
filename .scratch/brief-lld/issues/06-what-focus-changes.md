# What focus changes in the Brief

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 02

## Question

Request & Plan and Analysis leave `focus` to Brief. What does `--focus` change in the Market Brief: the order of Insights, how many cover that Dimension, the Summary, or the recommendations? How does it reach the writer, and what guarantees the other Dimensions still appear?

## Answer

Decided by the agent, on the user's instruction. `focus` changes emphasis only:

| Part | With `focus` |
|---|---|
| Insight order | `render` moves Insights of the focused Dimensions first, keeping the writer's order otherwise. This is code, so it always holds |
| Insight count | The writer is asked to give the focus most Insights. Prompt only: a count isn't worth a retry |
| Summary | The writer is asked to lead with it. Prompt only |
| Recommendations, Outlook, Confidence Tags, Stats | Nothing |
| Run Notes | `focus` is listed, so a reader knows why the Brief leans that way |

**It reaches the writer** as one line of the input, such as `Focus: compensation`, and all Stats are still sent. An empty `focus` says `Focus: none`.

**The guarantee is code, not a retry.** After the critic, `render` adds one Insight for every Dimension with Stats that no Insight cites, stating that Dimension's first Stat label as written, cited to that Stat. Stat order means it's the top item: the sample size, the first pay median, the top skill, the top employer, the top title. [Live check of the draft design](13-live-check-of-the-draft-design.md) found that a coverage error fed back didn't fix the draft, and 4 of 6 non-thin runs left a gap, so a retry would spend money and end in the rule-written Brief. This applies with or without `focus`, because the spec's five dimensions are the Brief's job either way. [Thin and empty Samples](07-thin-and-empty-samples.md) sets when it doesn't apply.
