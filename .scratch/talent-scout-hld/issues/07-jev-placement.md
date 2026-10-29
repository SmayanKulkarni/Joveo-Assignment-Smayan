# Where does Jev make routing decisions?

Type: grilling
Status: resolved

## Question

Which decisions use Jev's probabilistic outputs instead of an LLM, limited to semantic judgements that cannot be computed?

## Answer

Resolved during charting. Three placements:

1. **Clarity check**: is the role, location or seniority too ambiguous to search on? Drives clarify vs skip. An LLM still drafts the actual Clarifying Questions.
2. **Posting relevance**: is this Posting actually the researched role (vs keyword collisions)? Only Relevant Postings count toward Sufficiency.
3. **Critic** (stretch): is each Insight supported by the Postings it cites? Drives the revise loop.

Optional later: staffing agency vs direct employer.

Everything else is computed in code or produced by the LLM. Thresholds live in one place and are tuned per model (Jev calibration does not transfer between models). How Jev is reached on OpenRouter is open: see [Research: Jev on OpenRouter](12-research-jev-on-openrouter.md).
