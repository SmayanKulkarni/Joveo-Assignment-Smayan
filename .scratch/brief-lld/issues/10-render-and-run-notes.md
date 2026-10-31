# render and the Run Notes

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 02, 07

## Question

What does the Markdown look like for a client-facing reader, and how are Posting IDs shown so that every number can be traced without burying the page? How are the Run Notes built from `run_log` and the slices: Clarifying Questions and answers, the final Search Plan and `broadened_plans`, Postings analysed, Assumptions, every Caveat, and the `total` disclosure? Where does the replay banner go?

## Answer

Decided by the agent, on the user's instruction. `render` is plain code. `brief/markdown.py` holds one pure function, `render_markdown(brief, postings)`, with no clock, so a replayed Run gives the same bytes.

**Order, answers first:**

1. Replay banner, when `replayed`, as a quote above everything.
2. `# Market Brief: {role}, {location}`
3. `## Summary`, then the Weak Sample line from [Thin and empty Samples](07-thin-and-empty-samples.md).
4. `## Hiring Outlook`: the rating in bold, then its reason.
5. `## Client Recommendations`: title, band and skills, each with its reason, or "Not enough evidence to suggest…".
6. `## Insights`: `focus` order, each as `**[High]** text`, with the reason on the next line. Below them, the Confidence key from [Confidence Tag rules](03-confidence-tag-rules.md).
7. `## Run Notes`.
8. `## Evidence`.
9. `## Postings analysed`.

**Tracing without burying the page.** Each Insight and recommendation ends in a short reference: `Evidence: 35 Postings [E3]`. `## Evidence` then lists each `E3` with its full keys, and `## Postings analysed` is a table of key, title, company and link. So the first screen reads as a Brief, and every number gets to a real ad in two steps. `brief.json` holds keys on every part already, so it has no references.

`E` numbers count by order of appearance, with parts sharing the same Postings sharing a number. Posting text comes from outside, so `|` and newlines are removed from cells, and a link appears only for `http` and `https`.

**Run Notes, from the slices. Nothing is copied into `run_log`:**

| Line | From |
|---|---|
| Questions and answers, or "None asked" | `questions` |
| Assumptions, or "None" | `assumptions` |
| Focus, or "All Dimensions" | `focus` |
| Final Search Plan | `current_plan` |
| Earlier plans, or none | `search_plan` and `broadened_plans[:-1]`, when any broaden ran |
| Postings analysed, by source | `sample` |
| Source match counts | The last `collect` note holding `totals` |
| Caveats, every one, in order, as written | `run_log` entries of kind `caveat` |
| Jobs data attribution, when any Adzuna Posting is in the Sample | `ATTRIBUTION[Source.adzuna]` |

**`RunNotes` gains three fields** beyond [The Market Brief schema](02-brief-schema.md): `focus`, `match_totals: list[str]` and `attribution: str | None`. Routing decisions aren't in the Run Notes, since `scout --log` and the `samples/` traces carry those.

**The `total` disclosure** is one line per title and source: "Adzuna reported about 3,200 matches for Data Analyst. This is its own count, not a measure of demand." One line each, because titles overlap and summing them would double count. It never becomes a Stat or Evidence (Gateway §3).

**The replay banner** is Kernel §14's wording, from `settings.replay_cache`. `replayed` holds the same fact in `brief.json`.

**Stat figures aren't all shown.** `MarketBrief.stats` carries every one in `brief.json`, and the Markdown shows what the Insights and recommendations chose. A figures table was skipped, as coverage already gives every Dimension a line.

`render` writes `brief`, `brief_markdown`, the Caveat from [The critic](09-critic.md), and one `note` with the counts of Insights by tag. The Controller already writes the files (Runtime §7).
