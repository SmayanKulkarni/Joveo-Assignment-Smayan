# Brief view

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [Web API and hosting](03-web-api-and-hosting.md)

## Question

How does the finished Market Brief read in the browser, for a customer success manager who will hand it to a client?

- The layout of Summary, Insights (Confidence Tag, Evidence count and the cited Stats), Client Recommendations (title, salary band, top skills), the Hiring Outlook rating with its reason, and Run Notes (questions and answers, final Search Plan, Postings analysed, Assumptions, Caveats).
- How a Confidence Tag, the three Outlook ratings and a Caveat are made visible without relying on colour alone.
- Whether Evidence expands to show the cited Stats, and what a user can click through to.
- Rendering from `brief.json` structured data or from `brief.md`, and the JSON and Markdown downloads.
- An `aborted` Run, which has no Brief: what the page shows instead.
- A print-friendly view, if it costs a stylesheet only.

Resolution is the section order, the component per section and the data each reads.

## Answer

Decided by the agent (the user delegated every decision on 2026-10-31).

**Render from structured data, `RunDetail.brief` and `sample`, not `brief.md`.** Evidence needs to expand, and tags need components. It also means no Markdown renderer and no raw HTML, so Posting text from outside stays escaped by React. Downloads are the server's files.

**Section order is `brief.md`'s**, so the screen, the download and the print agree: the answer first, the working last.

| # | Section | Component | Reads |
|---|---|---|---|
| 1 | Title, Downloads | `BriefHeader` | `hiring_request.role`, `.location`; links to `brief.json`, `brief.md`; Print |
| 2 | Replay banner, Weak Sample notice | `BriefNotices` | `replayed`; `stats.sample_size < run_notes.final_plan.target_postings` |
| 3 | Summary | `Summary` | `summary` |
| 4 | Hiring Outlook | `Outlook` | `outlook` |
| 5 | Client Recommendations | `Recommendations` | `recommendations.job_title`, `.salary_band`, `.top_skills` |
| 6 | Insights | `Insights` | `insights`, and `/meta`'s `confidence_key` as a closed `<details>` |
| 7 | Run Notes | `RunNotes` | `run_notes` |
| 8 | Postings analysed | `PostingsTable`, closed `<details>` | `sample` |

The Weak Sample and "Not enough evidence" wording match `brief/markdown.py`. The replay banner is its `REPLAY_BANNER`.

**Never colour alone.**
- Confidence Tag: a pill with the word and a three-dot meter (●●● High, ●●○ Medium, ●○○ Low), then `confidence_reason` in plain text beneath.
- Hiring Outlook: a large rating word with a shape, ▲ Favourable, ◆ Competitive, ▼ Hard to fill, then the `reason`.
- Caveat: a warning icon and the word "Caveat" on each, in Run Notes.

**Run Notes stay open, not folded,** with Caveats first. The glossary says Caveats are always shown, and a closed fold would hide what most affects trust. Then Questions and answers, Assumptions, Focus, Final Search Plan, earlier plans, Postings analysed by source (counted from `posting_keys` prefixes), source match counts, attribution.

**Evidence is one `Evidence` component**, used by Insights, Recommendations and the Outlook. "Evidence: 38 Postings" is a button that expands inline to:
- The cited Stats, from `stat_ids` looked up in `brief.stats`: label, value and unit. These are what a figure rests on.
- The Postings, from `posting_keys` looked up in `sample`: title and company, linked to the source, ten at first with "Show all 38". `url` is already null unless http(s), and a null shows no link. Links use `target="_blank" rel="noopener noreferrer"`.

Two details from the types: `Evidence.count` is a Python property and isn't in the JSON, so the UI uses `posting_keys.length`. An Outlook at its default has empty `stat_ids` and shows no Evidence, as the Markdown does.

**Formatting.** A salary band is `low to high unit` with no decimals via `toLocaleString`, and a numeric Stat likewise, matching the Markdown. Missing recommendations show "Not enough evidence to suggest…". Zero Insights shows "None: this Brief has no findings."

**An `aborted` Run** shows the request, then "This Run ended without a Brief", the reason, a link to `/`, and the turns from `run_log`. No download links, and those endpoints return 404 `no_brief`.

**Print costs a stylesheet only.** `@media print` hides the sidebar, trace panel, the "How this Run went" fold and all buttons, and puts the column at full width. Closed `<details>` stay closed, so the complete Posting list belongs to the Markdown download.
