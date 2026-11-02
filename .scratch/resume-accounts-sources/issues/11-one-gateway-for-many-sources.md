# One gateway for many sources

Type: grilling
Status: open
Assignee: none
Blocked by: [What Arbeitnow does in the gateway](10-what-arbeitnow-does-in-the-gateway.md)

## Question

What is the smallest change that lets `JobsGateway` serve Arbeitnow beside Adzuna and USAJOBS, without building an abstraction before it's needed?

- `Fetch` checks `country` against `ADZUNA_CURRENCY`, and `fetch` hard-codes the USAJOBS rule. With three sources, where should "which countries and fields a source honours" live?
- Clients: today there's a `dict[Source, AdzunaClient | UsajobsClient]`, and each client has `search(f) -> Page`. Is a duck-typed `search` still enough, or does anything justify a `Protocol`?
- Quota: whether `Store.calls_left` needs a window per source, or Arbeitnow's snapshot needs no call guard at all.
- Caching: the L1 TTL for the Arbeitnow snapshot, and whether L2 (Adzuna only today) widens to it.
- `coalesce` and Duplicates across sources. Which Posting wins when the same job comes from two sources, and does `merged` still read well in the Run Notes?
- Salary mapping for each source under the Advertised and Estimated pay rule, and `region` and `domain` when a source has no place hierarchy or category.
- The Gateway LLD sections to update, and the `testing.py` fake the Arbeitnow client needs.

Load `langchain-router` if the answer reaches into tool code.
