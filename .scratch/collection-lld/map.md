# Collection LLD

Label: wayfinder:map
Parent: [Talent Market Scout: HLD](../talent-scout-hld/map.md) (component D in [docs/HLD.md](../../docs/HLD.md) §3, §4)

## Destination

`docs/lld/collection.md`: an LLD of Collection precise enough to build straight from, covering pass 1 (`search_jobs`, `fetch_agent`, `tools`, `collect`, `relevance`, Sufficiency, `broaden`, a pass-through `low_data_review`), pass 2 (the real `low_data_review`, USAJOBS-related Caveats) and pass 3 (tool event summaries), with nothing left to decide. Building the code is a separate effort after this map.

## Notes

- Domain: Collection turns an approved Search Plan into a Sample of Relevant Postings, broadening within a fixed limit and pausing when it can't get enough. Vocabulary: `GLOSSARY.md`. Spec: `Joveo_Talent_Market_Agent- Assessment.pdf`. Deadline Mon 2 Nov 2026, 9:00 AM, so this map stays lean.
- Fixed upstream: [docs/lld/kernel.md](../../docs/lld/kernel.md) §4–§7 (state, resets, routing), §9 (Caveats), §11 (Jev), §12 (Tiers), [docs/lld/runtime.md](../../docs/lld/runtime.md) §3–§5 (stage contract, wiring, Pause protocol), §10 (events), [docs/lld/gateway.md](../../docs/lld/gateway.md) §3, §5, §6, §17 (`Fetch`, errors, `coalesce`, hand-ons), [docs/lld/request-plan.md](../../docs/lld/request-plan.md) §6 (`SearchPlan` limits), HLD §4, §6.
- Skills: `langchain-router` first for any framework question (per `CLAUDE.md`); `grilling` + `domain-modeling` for grilling tickets.
- Standing preferences: inherited from the Kernel map (Pydantic v2 everywhere, `uv`, Python 3.12, `src/talent_scout/`, `pytest`, root `.env`).
- All grilling tickets were resolved in one session, in two rounds, on 2026-10-31.

## Decisions so far

<!-- one line per closed ticket -->

- [The fetch agent and search_jobs](issues/01-fetch-agent-and-search-jobs.md): one tool taking only `title` and `page`, cheap tier, 6 Fetches per Attempt, with results in their own slice and only a summary in messages.
- [What Relevant means and how it is judged](issues/02-relevance.md): role only, one Jev request per Posting, verdicts kept across Attempts, and the Sample draws on every Attempt.
- [Sufficiency, broaden and blocked Attempts](issues/03-sufficiency-broaden-and-blocked-attempts.md): `len(sample) >= target` with 2 broadens, USAJOBS counted, `broaden` can't touch country or target, and `fetch_blocked` skips straight to the Pause.
- [The low_data_review Pause](issues/04-low-data-review.md): the payload shows counts, plans and the block reason; the answer is an action plus optional guidance, and `broaden` is always allowed.
- [Who builds the Sends](issues/05-who-builds-the-sends.md): Collection's routers return `"analyse"`, and Runtime turns it into Analysis's `fan_out(state)`.
- [Caveats](issues/06-caveats.md): eight Caveats with fixed triggers and writers, source `total` as a `note`, and no Caveat for a normal L2 read.
- [Prompts](issues/07-prompts.md): the LLD fixes each prompt's inputs and rules, wording lives in `collection/prompts.py`, and "yes" on the relevance Noul means really this role.
- [Write docs/lld/collection.md](issues/08-write-collection-lld-doc.md): the LLD is written and the HLD, Kernel, Gateway, Runtime, Request & Plan and future-scope docs agree with it, with `FetchRecord` replacing `fetch_results` while writing.

## Not yet specified

## Out of scope

- Batching, `fan_out`'s body and federal pay in Stats: Analysis LLD.
- Rendering Caveats and the `total` disclosure: Brief LLD.
- Choosing the three sample runs within the Adzuna budget: Delivery.
- A daily budget shared across concurrent Runs: Infra shell LLD.
- Writing the Collection code: separate build effort after this map.
