# Charts in the Brief

Type: prototype
Status: resolved
Assignee: smayankulkarni05
Blocked by: [A Brief you can read at a glance](16-a-brief-you-can-read-at-a-glance.md), [Many places and titles in a Search Plan](13-many-places-and-titles-in-a-search-plan.md)

## Question

Which charts earn a place in the Brief, what data backs each one, and how are they drawn?

Consult the `dataviz` skill and prototype against a real Brief from `runs/`.

- Locations: `PostingRef.location` is already on the wire, but raw strings need grouping, and `Posting.region` is not sent.
- Pay: `MarketStats` only holds p25, median and p75, so a range bar works today. A true distribution needs per-Posting figures added server-side. Salary is often missing or estimated, so the chart must show how many Postings it rests on and hide below a minimum.
- Skills: top skills from the `skills.*.count` Stats, split into required and nice to have.
- Also consider posting age and employer or seniority mix, only if each answers a question a client asks.
- Every number must come from a Stat or the Sample, never from the LLM, and should link to its Evidence.
- Drawing: hand-written SVG, as the trace graph is, unless the charts show that a library pays for itself. Reading without colour alone, screen-reader text, phone width and print.
- `brief.md` has no charts: is the data there as text already?

## Answer

Decided by the agent, as the user told it to make every decision on 2026-11-01. Open to change once the user reads it.

[Prototype](../prototype/look/index.html) on both real Briefs, checked at phone width. Palette run through the `dataviz` validator.

Four small charts earn a place, each answering a client's question:

| Chart | Question | Data | Hidden when |
|---|---|---|---|
| Pay, middle 50% | What should we pay? | The Salary band's own `stat_ids`, so it can't disagree with its tile. p25 to p75 box, a median line, both ends labelled, "from 28 postings" | No Salary band, which already needs 5 figures |
| Skills employers ask for | What leads the job description? | `skills.*.count`, top 8 from 2+ employers, the required part from `skills.*.must` | No such skills |
| Where the postings are | Is the market where I asked? | Sample `region`, grouped | Under 2 groups |
| Who is hiring most | Who am I up against? | Top 5 `competition.employer.*`, plus `competition.distinct_employers` | No employers |

- **Rejected.** A per-Posting pay distribution needs new server data and salaries are sparse. A posting-age chart: the trend is one word already and tilts recent, so it's a line in the Insights. Seniority mix: the real Marketing Run is 100% unknown.
- **Skills from one employer are left out and the caption says so.** In the real Marketing Run, one employer alone accounted for reels and X (Twitter), 9 postings each.
- **Places group from the data.** Strip what all Postings share, then group by the next `region` level, so a metro search shows areas and a country-wide one shows states. Real result: Mumbai 25, Thane 3, Navi Mumbai 2. Top 6, then "N other places". A Posting whose region is only the country counts as "Area not given": 15 of 51 in the real country-wide Run, and they must not stop the grouping.
- **One pure server function, `brief/glance.py`.** `glance(brief, postings)` returns `reader_notes` and chart rows, each with its Evidence keys, and goes on `RunDetail`. The UI only draws. Numbers come from Stats or the Sample, never the LLM, and earlier Runs get charts.
- **Drawing: HTML and CSS, not SVG.** Every chart is horizontal bars or one range, so widths on real text rows are the shortest thing that works, and give screen readers and print the labels for free. No library. Clicking a row opens its Evidence. A native `title` gives the hover.
- **Colour.** One hue: `--chart #00795f`, and `--chart-2 #2fb08f` for the non-required part of a skill bar. They pass the validator's lightness, chroma and colour-blind checks on `--bg`. `--chart-2` is 2.38:1, a warning that needs visible labels, and every bar has its number, so it's met. The "dark is required" caption shows only when a required count exists. Print forces colour with `print-color-adjust: exact`.
- **`brief.md`** has no charts and only part of this data, so `render_markdown` gains `## Market figures`: pay, skills, places and employers as plain lists from the same `glance`.
