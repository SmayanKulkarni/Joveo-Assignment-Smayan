# A Brief you can read at a glance

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [Subtle neumorphic look and compact layout](14-subtle-neumorphic-look-and-compact-layout.md), [What the user sees and what the record keeps](15-what-the-user-sees-and-what-the-record-keeps.md)

## Question

How does the Market Brief give its answer in seconds, with detail only on request?

- The first screen: the Outlook, the recommended title, salary band and top skills, as scannable cards rather than one long column.
- Insights: the limit on how many show first, one line each, with the confidence reason and Evidence folded away. Does the `write_brief` prompt need shorter text, or is this display only? The Critic and citations must keep working either way.
- Where Summary, Evidence, Postings analysed and the remaining Run Notes go.
- How the Weak Sample notice and the short Caveats from the ticket above appear without taking over the page.
- Whether screen, Markdown and print still agree on wording, given `BriefView.tsx` copies `brief/markdown.py`'s wording on purpose.

## Answer

Decided by the agent, as the user told it to make every decision on 2026-11-01. Open to change once the user reads it.

- **First screen, in order:** title; four tiles (Hiring Outlook with its shape and word, Job title, Salary band, Top skills, up to 4); reader notes; the Summary; then charts. Outlook and recommendation reasons open from a "Why" fold on each tile, with Evidence inside. A missing recommendation shows "Not enough evidence" in muted text. Four tiles become two columns on a phone.
- **Insights.** "What we found" shows 3, highest confidence first and stable within a level, with "Show all 8" below. Each is its pill and text, with the reason and Evidence in a fold. Display only, nothing is dropped.
- **One small prompt change.** `InsightDraft.text`'s description asks for one sentence of at most 20 words. Text is never truncated on screen, as cutting could remove a figure. The Critic and citation checks don't change, as they read the same fields.
- **Below:** "How this was researched" holds Run Notes, then "Postings analysed", both closed. Downloads stay top right, quieter. The attribution line is last.
- **Notices.** The replay banner stays. A reader note is one slim tinted line with a warning icon, at most two. The Weak Sample notice is one of those notes, so it can't appear twice.
- **Screen and Markdown agree on facts, not wording.** Screen is for the reader and Markdown is the record, so `BriefView.tsx` drops its copied strings and comment. A pytest checks that the figures in `reader_notes` come from the Brief. Print follows the screen, with folds closed, and the Markdown is the full version. Also fixes "with a entry level" in `outlook()`'s reason.
