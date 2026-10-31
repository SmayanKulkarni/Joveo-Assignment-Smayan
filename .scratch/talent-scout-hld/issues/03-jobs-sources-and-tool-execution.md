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

**Update from [Gateway query interface](../../gateway-lld/issues/02-gateway-query-interface.md) (2026-10-30):** the two source tools become one `search_jobs` tool. The Gateway picks sources by rule (Adzuna always, USAJOBS when the country is `us`), fans out, merges and collapses Duplicates, so the model no longer chooses the source.

**Update (2026-10-31), reversing the update above:** back to two tools, `search_adzuna` and `search_usajobs`, because the spec evaluates tool calling and a router inside one tool hides the model's choice. See the [Collection LLD](../../../docs/lld/collection.md) §5.
