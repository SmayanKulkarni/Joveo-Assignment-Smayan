# 01: Adzuna through fetch

**What to build:** a stage can call `make_gateway(settings)`, open it with `async with`, and `fetch` one page for a `Fetch`, getting coalesced Postings back. A source failure comes back as a result field or a clear error, and no failure path can leak the Adzuna keys. Spec: [Gateway LLD](../../../docs/lld/gateway.md) §2, §3, §5, §6, §7.1, §7.2, §16 pass 1 steps 1-3.

Out of scope: the budget guard and L1 (ticket 02), so nothing here is cached or counted yet. Tests use `httpx.MockTransport` and spend no live quota.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] `httpx` is pinned directly at the installed version
- [x] Test: the `Fetch` validator normalises text, equal Fetches dump equal JSON, and a country outside `ADZUNA_CURRENCY` is rejected
- [x] Test: the Adzuna search fixture gives 50 Postings through `fetch`, with no `utm_` params in `url`, `predicted` true, and non-Domain tags mapped to `None`
- [x] Test: reversed and missing salaries map as §7.2 says, and a blank `location` omits `where` and `distance`
- [x] Test: a bad result is counted in `dropped` and the rest still return, while no salary, no company or a non-Domain category isn't a drop
- [x] Test: Deloitte and Capital One collapse into one survivor each with `merged` filled, Booz Allen stays apart, and the survivor order holds
- [x] Test: a timeout, connect error or 5xx retries twice then ends in `failures[adzuna]`, and `fetch` raises `GatewayError` when no source returned anything
- [x] Test: a body without `results` is `SourceUnavailable`
- [x] Test: a `401` raises `SourceRejected` carrying source, status and body, with no key or URL in its message
- [x] `raise_for_status()` is never called, `SourceUnavailable` is raised `from None` with fixed text, and `make_gateway` sets the `httpx` logger to WARNING
- [x] `FakeGateway(results)` returns canned `FetchResult`s from `fetch`, so stage tests can start against it
- [x] `ATTRIBUTION[Source.adzuna]` is exported
