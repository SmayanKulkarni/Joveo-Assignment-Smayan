# Research: searching many titles and places on Adzuna

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

What can one Adzuna call cover, and so what do many titles and many places cost against the quota?

- Can several titles share one call (`what_or`, or `what` with phrases), and how does that change `count`, ranking and relevance?
- Can `where` take several places, or does each place need its own call? How do `where` and `distance` behave for Indian places such as Navi Mumbai and Thane, and does a wide radius around Mumbai already cover them?
- What are the current free-tier limits? The code assumes 25 calls a day (`MAX_FETCHES` in `collection/nodes.py`).
- Does USAJOBS accept several `LocationName` values or several keywords in one call?

Use primary sources: Adzuna's and USAJOBS's own API docs. Say which answers are documented and which still need a live call.

## Answer

Full findings, with sources: [research-adzuna-many-titles-and-places.md](assets/research-adzuna-many-titles-and-places.md). No API search was called. Budget on calls = titles x places x pages.

- **Several titles in one call: documented no, for multi-word titles.** `what_or` ORs single keywords and `what_phrase` takes one phrase, so `count` would stop measuring a title. Sharing is only sensible for single-word variants. **Needs a live check:** `what_or` combined with `title_only`, quoted phrases, and whether `title_only` needs every word.
- **Several places in `where`: documented no.** `where` is one centre, `distance` is in km, and `locationN` is one hierarchy path, though it can cover a region.
- **Navi Mumbai, Thane and a wide Mumbai radius: needs a live check.** Nothing about Indian places is documented. About 4 calls would settle it.
- **Free-tier limits: no public number is documented.** The terms defer to the account. The project records 25 a day from the dashboard, worth re-reading. `MAX_FETCHES` is actually 6 per Attempt; the 25 is `adzuna_daily_limit`.
- **USAJOBS: documented** that `LocationName` takes several `;`-separated values, and `Keyword` and `PositionTitle` are not marked multi-value. **Needs a live check:** several locations with `Radius`.
