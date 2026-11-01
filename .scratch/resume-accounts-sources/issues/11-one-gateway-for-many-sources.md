# One gateway for many sources

Type: grilling
Status: open
Assignee: none
Blocked by: [Which job sources join the gateway](10-which-job-sources-join-the-gateway.md)

## Question

What is the smallest change that lets `JobsGateway` serve the chosen sources, without building an abstraction before it's needed?

- `Fetch` checks `country` against `ADZUNA_CURRENCY`, and `fetch` hard-codes the USAJOBS rule. Once there are five or six sources, where should "which countries and fields a source honours" live?
- Clients: today there's a `dict[Source, AdzunaClient | UsajobsClient]`, and each client has `search(f) -> Page`. Is a duck-typed `search` still enough, or does anything justify a `Protocol`?
- One RapidAPI HTTP helper for the key, host and quota headers, or each client on its own?
- Quota: `Store.calls_left` per source with daily or monthly windows, and reading quota headers from the response.
- Caching: L1 TTLs per source, and whether L2 (Adzuna only today) widens to other sources.
- `coalesce` and Duplicates across sources. Which Posting wins when the same job comes from two sources, and does `merged` still read well in the Run Notes?
- Salary mapping for each source under the Advertised and Estimated pay rule, and `region` and `domain` when a source has no place hierarchy or category.
- The Gateway LLD sections to update, and the `testing.py` fakes each new client needs.

Load `langchain-router` if the answer reaches into tool code.
