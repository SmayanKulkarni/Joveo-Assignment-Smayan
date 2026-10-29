# Which jobs sources are used, and how are tools executed?

Type: grilling
Status: resolved

## Question

Which public jobs APIs feed the agent, how are they exposed to the model, and what runs the tool calls?

## Answer

Resolved during charting.

- **Adzuna** is the primary source (multi-country, salary fields; 25 requests/day budget).
- **USAJOBS** is a secondary tool, used by the model only for US locations (federal roles only).
- Both are standard LangChain `@tool`s bound to the fetch model, so the model decides which to call.
- Tool calls run through a **custom tool executor node** (reads `tool_calls`, dispatches by name, returns `ToolMessage`s) instead of the prebuilt `ToolNode`, to insulate from LangChain internals churn. This satisfies "ToolNode or equivalent" and is fully explainable live.
- Tools never call the APIs directly; they go through the Jobs Data Gateway (see [Jobs Data Gateway caching and expiry](04-jobs-data-gateway-caching-and-expiry.md)).
