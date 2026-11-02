# Matching Postings to a Resume

Type: grilling
Status: open
Assignee: none
Blocked by: [What a Resume is for](17-what-a-resume-is-for.md), [Research: reading resume files](08-research-reading-resume-files.md), [Choosing among the search tools](12-choosing-among-many-search-tools.md)

## Question

How does the resume agent turn a parsed Resume into searches, and how does it score and explain each Match?

- From Resume to search: which titles, places and seniority it searches, whether the user approves that plan at a Pause, and whether the User Profile changes it.
- Scoring a Posting against a Resume: overlap of the skills in the Extraction with the resume's skills (by code), seniority and years fit, place and remote fit, and any LLM or Jev judgement. Which parts are computed and which are judged, and how a score stays explainable (the skills matched and the skills missing).
- Ranking, cut-off and how many Matches are shown. Ties and Duplicates.
- Costs: the LLM calls per Posting and how they're batched (reuse Batches?), and the extra Adzuna calls against its daily guard.
- Honesty: never claim a skill match that isn't in both texts, and record Assumptions in the Run Notes.
- The graph nodes and state fields this adds, and the LLD section that owns them. Load `langchain-router` first.
