# Jobs Data Gateway LLD

Label: wayfinder:map
Parent: [Talent Market Scout: HLD](../talent-scout-hld/map.md) (component B in [docs/HLD.md](../../docs/HLD.md) §3, §7)

## Destination

`docs/lld/gateway.md`: an LLD of the Jobs Data Gateway precise enough to build straight from, covering every tier (pass 1: Adzuna client, L1 cache, budget guard, replay; pass 2: USAJOBS, L2 region × Domain store, expiry and sweep), with nothing left to decide. Building the code is a separate effort after this map.

## Notes

- Domain: the Gateway sits outside the graph, between Collection's `@tool`s and the jobs APIs, and protects a small daily Adzuna quota. Second in the must-have walking skeleton, after the Kernel. Vocabulary: `GLOSSARY.md`. Spec: `Joveo_Talent_Market_Agent- Assessment.pdf`. Deadline Mon 2 Nov 2026, 9:00 AM.
- Fixed upstream: [docs/lld/kernel.md](../../docs/lld/kernel.md) §3 (Posting, Salary, Source, mapper duty, `source:source_id` key), §9 (Caveats the Gateway feeds), §13 (one `Settings` object), §14 (`REPLAY_CACHE` switches jobs-data replay too), §15 (Jobs APIs test seam left to this LLD). HLD §7 and [Gateway caching and expiry](../talent-scout-hld/issues/04-jobs-data-gateway-caching-and-expiry.md). API facts: [Research: Adzuna API facts](../talent-scout-hld/issues/13-research-adzuna-api-facts.md), [Research: USAJOBS API facts](../talent-scout-hld/issues/14-research-usajobs-api-facts.md).
- Skills: `langchain-router` first for any framework question (per `CLAUDE.md`); `grilling` + `domain-modeling` for grilling tickets.
- Scope rules (decided at charting):
  - **Boundary with Collection.** The Gateway owns a typed Python interface (`Fetch` in, `FetchResult` out) and everything behind it: source choice and fan-out, HTTP clients, mappers, Duplicate coalescing, L1, L2, budget guard, expiry, sweep, replay, test fake. Collection owns the one LLM-facing `search_jobs` tool schema and the tool-args → `Fetch` translation. Both types live in the `gateway/` package, not the Kernel.
  - The Gateway supplies the data a Caveat needs; Collection decides when to raise one and its wording.
- Standing preferences: inherited from the Kernel map (Pydantic v2 everywhere, `uv`, Python 3.12, `src/talent_scout/`, `pytest`, root `.env`). Live Adzuna calls are budgeted: about 5 approved for the smoke test; anything more needs the user's OK.

## Decisions so far

<!-- one line per closed ticket -->

- [Live smoke test: Adzuna and USAJOBS](issues/01-live-smoke-test-adzuna-usajobs.md): Adzuna silently caps pages at 50, sends no rate-limit headers, leaks our app id in `redirect_url`, and returned only predicted point salaries; USAJOBS items are ~85 KB with up to 1,176 locations, `;` separates values, Radius acts like miles, and a per-Posting remote flag exists; fixtures in `tests/fixtures/jobs/`; quota still unreported.
- [Gateway query interface](issues/02-gateway-query-interface.md): plain async Python `JobsGateway.fetch(Fetch) -> FetchResult`. It fans out to Adzuna (always) and USAJOBS (`country == "us"`) and merges them behind one `search_jobs` tool, one page per source per call, one title per Fetch. It coalesces Duplicates with a pure title + employer + description-prefix rule. Per-source failures are a result field; auth errors stop the Run.
- [Adzuna client and mapper](issues/03-adzuna-client-and-mapper.md): `title_only` + `where`/`distance` (blank location = country-wide), `sort_by=date`, 50 per page; a 19-country → currency table that `Fetch` validates against; four non-occupational category tags → `None` Domain; `utm_*` stripped from the URL; drops are per-result mapping errors; 10 s timeout, 2 retries, 429 → `BudgetExhausted`, 401/403 propagate.
- [L1 cache, budget guard and replay](issues/04-l1-cache-budget-guard-and-replay.md): own SQLite file; L1 stores mapped Postings, refetches after 24 h and deletes a row only when all its Postings have closed; Adzuna limit is 25/day, spent per HTTP attempt and locked for the UTC day on a 429; replay is a read-through file in front of L1; tests use `httpx.MockTransport` and `FakeGateway`.
- [Adzuna aggregate endpoints](issues/06-adzuna-aggregate-endpoints.md): `histogram`, `top_companies`, `history` and the search `mean` are excluded from every pass, since they carry no Posting IDs and add little; `SourceOutcome.total` may appear only as labelled sampling disclosure, never as a Stat, Evidence or demand figure.
- [USAJOBS client and mapper (pass 2)](issues/05-usajobs-client-and-mapper.md): `PositionTitle` (matches any word) in relevance order, 50 per page, `DatePosted` capped at 60, category ignored; description starts with `JobSummary`, cut at 4,000; `source` alone labels federal pay; multi-location Region is the common prefix; a static family → Adzuna tag table with `None` for no match; a 429 is `SourceUnavailable`, no lockout.
- [L2 store, expiry and sweep (pass 2)](issues/07-l2-store-expiry-and-sweep.md): an Adzuna-only table that serves page N only if it can fill it, reuses a Posting only for a `Fetch` no broader than the one that found it, and also backs failed live calls with `cache=store`; expires 7 days after Adzuna last returned a Posting; purges after each live write, not at Run start; `Fetch` needs no target.
- [Write docs/lld/gateway.md](issues/08-write-gateway-lld-doc.md): [docs/lld/gateway.md](../../docs/lld/gateway.md) written, with the pass 1 and pass 2 build checklists; Kernel §15's Jobs APIs row filled; errors must never use `raise_for_status()`, which would leak the Adzuna keys.

## Not yet specified

## Out of scope

- Shared daily Adzuna budget across concurrent Runs, persistence migration off SQLite, moving L1 and the budget guard to MiniStack if required: Infra shell.
- Whether the replay Caveat also reports live calls made during replay (`SourceOutcome.cache == miss`): Collection LLD.
- Sample-run strategy for the three `samples/` requests within the Adzuna budget: delivery task.
- Caveat wording and when Collection raises one: Collection LLD.
- Rendering the "The Adzuna API" attribution in Run Notes (the Gateway only exports the string, per [Adzuna client and mapper](issues/03-adzuna-client-and-mapper.md)): Brief LLD.
- LLM-facing tool schemas: Collection LLD.
- Re-applying `coalesce` across Fetches in `collect`, and the `run_log` note for merged Duplicates: Collection LLD.
- Keeping federal pay (`source == usajobs`) apart from Adzuna salary Stats: Analysis LLD, per [USAJOBS client and mapper (pass 2)](issues/05-usajobs-client-and-mapper.md).
- Telling the Relevance stage about FAA "Public Notice" talent-pool announcements and `PositionTitle`'s any-word matches: Collection LLD.
- Wording and placement of the `SourceOutcome.total` sampling disclosure, which can't use `total` when `cache == store`: Collection and Brief LLDs.
- Whether an L2 answer's age (`cache == store`, `fetched_at`) raises a Caveat: Collection LLD.
- Listing the aggregate exclusion in the README's known limitations: delivery task.
- Writing the Gateway code: separate build effort after this map.
