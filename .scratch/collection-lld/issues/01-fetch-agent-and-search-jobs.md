# The fetch agent and search_jobs

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

What does the model control when fetching, how do Postings get from a tool call to `collect` without filling the message history, and what stops the agent?

## Answer

Decided by grilling.

- **`search_jobs(title, page=1)`.** Country, location, radius, `max_days_old` and category are pinned by code from `current_plan`, so the model can't drift from the plan the user approved. The title may be any string, not only one from the plan, because the model's judgement on variants is the point of having an agent.
- **One tool, disclosed.** The spec says "use tool calling so the model decides which tool to use", while the Gateway LLD fixed one tool. The model decides titles, pages and when to stop, but never which tool. A second tool such as `get_search_status` would only repeat what tool messages say, so it isn't built. The write-up says so.
- **`fetch_results: list[FetchResult]`.** A new Collection slice written by `tools`, read by `collect` and cleared by `broaden`. `ToolMessage.artifact` is untyped, so strict msgpack blocks models there, and 50 Postings per call don't belong in history.
- **The model sees a summary:** new-Posting count, each source's total, `calls_left`, failures and a few sample titles.
- **`collect`** re-applies `coalesce` across Fetches. The mappers already normalise.
- **Cheap tier, 6 Fetches per Attempt.** Over 3 Attempts that is at most 18 Adzuna calls from the 25-a-day limit, not counting retries. At the cap, `tools` refuses further calls with a `ToolMessage` and the router goes to `collect`.
- **Over-fetching.** The agent can't see relevance until later, so its prompt asks for about 1.5× `target_postings` raw.

**Executor errors:**
- Bad args, an unknown tool name or a `GatewayError` become a `ToolMessage` the model can read.
- `SourceRejected` and bugs propagate and stop the Run.
- Several calls in one turn run concurrently, and any over the cap are refused individually.
- An Attempt where the model makes no tool call counts as a normal Attempt with a logged `warning`, rather than adding a retry path for something rare.
- `LLMExhausted` propagates from `fetch_agent`.
