# Matching Postings to a Resume

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [What a Resume is for](17-what-a-resume-is-for.md), [Research: reading resume files](08-research-reading-resume-files.md), [Choosing among the search tools](12-choosing-among-many-search-tools.md)

## Question

A Run has two deliverables, and [What a Resume is for](17-what-a-resume-is-for.md) added a matching stage for the Customer Recommendation. How does it score and explain each Match?

- Which Postings get matched: only the Sample the Brief uses, or more? The search answers the Hiring Request, so does a Resume-drafted request search well enough for both deliverables?
- Where matching sits among the stages, and whether it can fail without losing the Brief.
- Scoring a Posting against a Resume: overlap of the skills in the Extraction with the resume's skills (by code), seniority and years fit, place and remote fit, and any LLM or Jev judgement. Which parts are computed and which are judged, and how a score stays explainable (the skills matched and the skills missing).
- Remote Postings: [Choosing among the search tools](12-choosing-among-many-search-tools.md) shows them to everyone with a label such as "Remote: check where the employer can hire". Where that label goes, and whether a Match's score accounts for it.
- Ranking, cut-off and how many Matches are shown. Ties and Duplicates.
- Costs: the LLM calls per Posting and how they're batched (reuse Batches?), and the extra Adzuna calls against its daily guard.
- Honesty: never claim a skill match that isn't in both texts, and record Assumptions in the Run Notes.
- The graph nodes and state fields this adds, and the LLD section that owns them. Load `langchain-router` first.

## Answer

Decided by the agent alone on 2026-11-02, at the user's request, with no grilling. The decisions are in [Final decisions](../final-decisions.md#matching-postings-to-a-resume).
