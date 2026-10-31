# 02: Fetches become a Sample, and a Sufficient Sample moves on

**What to build:** an Attempt's records merge into `postings`, Jev judges each new Posting against the researched role, and the Relevant ones form the Sample. A Sufficient Sample leaves Collection through the `"analyse"` outcome and reaches `stats` in the graph. `fetch_blocked` is set here so that the next ticket can route on it. Spec: [Collection LLD](../../../docs/lld/collection.md) §4, §6, §7, §8, §11, §12, §14 pass 1 steps 4-5, and the `"analyse"` part of step 7. [Runtime LLD](../../../docs/lld/runtime.md) §4.

**Blocked by:** 01: Collection contract and the model's searches.

**Status:** ready-for-agent

`collect`:

- [ ] Plain code that reads only the current Attempt's records, with no LLM call
- [ ] Merges by key first, with the first copy seen winning, then applies `coalesce` to the result
- [ ] Strips Postings from those records and keeps everything else on them, such as totals and `error`
- [ ] Writes a `note` with the count kept and Duplicates merged. Merged Duplicates are never a Caveat
- [ ] Writes a `note` with source totals as `{title: {source: total}}`, leaving out `cache == store`
- [ ] Test: the same key from two Attempts stays one Posting with no self-merge
- [ ] Test: a Duplicate across Fetches collapses
- [ ] Test: records lose their Postings but keep totals, and `store` totals are left out of the note

`relevance`:

- [ ] Each key in `postings` with no verdict gets one `jev.judge("relevance", state, {"relevant": RELEVANT_NOUL})` under `asyncio.gather`, with the Kernel's semaphore limiting concurrency
- [ ] The state sent is `role` and `seniority` from `hiring_request`, and the Posting's `title`, `company`, `domain` and `description`
- [ ] Verdicts are kept across Attempts, so later Attempts judge only new Postings
- [ ] `sample` is `[k for k in postings if relevance_verdicts[k]]`, recomputed each Attempt, drawn from every Attempt and never capped
- [ ] Relevant means role only: unlevelled and junior Postings are Relevant, while a keyword collision or a FAA "Public Notice" talent pool isn't
- [ ] `RELEVANT_NOUL` in `prompts.py` follows every §12 rule, with "yes" meaning really this role and both or neither criteria sides set
- [ ] `fetch_blocked` is written on every pass: "Every search in this Attempt failed: <error>" when the Attempt has records and all have `error`, and "Adzuna's daily limit is used up, until the next UTC day" when `calls_left(Source.adzuna) == 0`, `country != "us"` and `replay_cache` isn't set. Otherwise it's `None`
- [ ] Writes a `route` log with the count, target and outcome, e.g. "38 of 142 Postings relevant (route: broaden)"
- [ ] Jev errors that survive its own retries and fallback propagate, and `scout resume` reruns the node
- [ ] Test with `fake_classifier`: only unjudged Postings are sent, and the Sample drops a key that `coalesce` merged
- [ ] Test: both `fetch_blocked` reasons fire, a US Run isn't blocked by an empty Adzuna budget, and replay skips the budget check

Routing:

- [ ] `after_relevance` returns `analyse` when `len(sample) >= current_plan.target_postings`, then `low_data_review` when blocked or at `MAX_BROADENS`, otherwise `broaden`. USAJOBS Postings count the same as Adzuna's, with no separate noise rule
- [ ] `build_graph` wraps Collection's two routers so `"analyse"` becomes `fan_out(state)`, and until Analysis lands the stub in `runtime/testing.py` returns `"stats"`
- [ ] `CONDITIONAL["relevance"]` gains `stats`, which the stub `fan_out` returns and the current target list lacks
- [ ] Test: every `after_relevance` outcome
- [ ] Test: a graph run with other stages stubbed goes from `fetch_agent` to `stats` when the first Attempt is Sufficient
