# What does the LLM do versus deterministic code?

Type: grilling
Status: resolved

## Question

Where is the line between LLM work and deterministic code, given that every number in the Market Brief must trace back to real Postings? Should analysis be a tool the LLM calls?

## Answer

Resolved during charting.

- **LLM extracts per-Posting facts**: normalised skills, seniority, must-have vs nice-to-have, years of experience.
- **Python computes every number**: counts, salary median and middle 50%, pay-disclosure share, top employers, posting-date trend.
- The brief writer receives precomputed stats plus Posting IDs; it phrases and selects Insights, never invents figures.
- Analysis runs as a **separate deterministic `stats` node**, not as a tool: there is no decision for the model to make (stats always run), and a tool would add nondeterminism, tokens and a failure mode while hiding a fixed step inside the model loop.
- **Sufficiency** is a code/rule decision over API-returned data (Relevant Posting count vs the Search Plan target, capped attempts), not an LLM opinion. Exact numbers are LLD.
