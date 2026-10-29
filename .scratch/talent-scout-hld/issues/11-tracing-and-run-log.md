# How are Runs traced and explained?

Type: grilling
Status: resolved

## Question

How are routing decisions made visible to evaluators, who may not have access to the LangSmith project?

## Answer

Resolved during charting.

- **LangSmith** traces everything.
- The graph also keeps its own **run log in state**: routing decisions with reasons, Clarifying Questions and answers, the final Search Plan. It feeds the Market Brief's Run Notes and the `samples/` transcripts, so samples stand on their own without LangSmith access.
