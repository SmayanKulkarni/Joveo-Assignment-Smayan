# Choosing among the search tools

Type: grilling
Status: open
Assignee: none
Blocked by: [What Arbeitnow does in the gateway](10-what-arbeitnow-does-in-the-gateway.md), [One gateway for many sources](11-one-gateway-for-many-sources.md)

## Question

How does Collection's fetch model choose among `search_adzuna`, `search_usajobs` and an Arbeitnow tool, and how is the budget shared out?

- One tool per source (as `search_adzuna` and `search_usajobs` are today), or one `search(source=...)` tool? What must each tool description say so the model picks well: coverage, cost, and the fields it ignores.
- `_bound`: which tools are offered for which plan (country, remote, kind of role), so the model is never offered a tool that can't work.
- `MAX_FETCHES`, `RAW_FACTOR` and `_cap` with a third source. Is there a per-source cap inside an Attempt?
- How broaden and the low-data review treat a source that ran out of quota or failed.
- Whether the resume agent (see [Matching Postings to a Resume](18-matching-postings-to-a-resume.md)) reuses these tools unchanged.
- The Collection LLD sections and prompts (`collection/prompts.py`) to update.

Load `langchain-router` first: this touches LangGraph tool binding and the custom executor.
