# 03: Broadening, pass 1 Caveats and the live smoke

**What to build:** finishes pass 1. A short Attempt broadens within the limit and tries again, and when it still can't get enough, the Run carries on through a pass-through `low_data_review` to analysis. The Run log says plainly what happened to the data. A live run through the real models and Adzuna then proves the whole stage. Spec: [Collection LLD](../../../docs/lld/collection.md) §4, §9, §10 (pass 1), §11, §12, §14 pass 1 steps 6-9.

**Blocked by:** 02: Fetches become a Sample. Also from `.scratch/request-plan-build`: 01 (`SearchPlan` limits), 03 (the clarify loop) and 04 (Search Plan and pass-through `plan_review`), since the live smoke needs a real `search_plan`.

**Status:** done

`broaden`:

- [x] Uses `tiers.structured("strong", SearchPlan, system=BROADEN_SYSTEM, name="broaden")`, and `LLMExhausted` propagates
- [x] Code pins `country` and `target_postings` to the current plan's values, and a violation of the other limits is fed back on the retry
- [x] Appends to `broadened_plans`, clears `messages` to `[]`, and writes a `note` with what changed
- [x] The input holds `hiring_request`, the current plan, the Sample count and target, each title and page searched with its source totals, up to 10 rejected Posting titles, and `low_data_guidance` when set
- [x] `BROADEN_SYSTEM` in `prompts.py` follows every §12 rule, with stable text first
- [x] Test: the LLM's `country` and `target_postings` are overwritten, `messages` is cleared, a bad plan passes on the feedback retry, and guidance reaches the prompt

Pass-through `low_data_review` and routing:

- [x] `make_nodes` exports a `low_data_review` that doesn't interrupt, leaves `low_data_decision` null and still logs the closing Caveats
- [x] `after_low_data` returns END on `abort`, `broaden` on `broaden`, and `analyse` on `continue` or null
- [x] Test: every `after_low_data` outcome
- [x] Test: a graph run with other stages stubbed has too few Postings on the first Attempt, broadens, then reaches Sufficiency
- [x] Test: a graph run that stays short gets 3 Attempts, passes through `low_data_review` and reaches `stats`, including with a Sample of zero
- [x] Test: `fetch_blocked` skips straight to `low_data_review` with broadens left

Pass 1 Caveats, each with a trigger and a non-trigger test:

- [x] Postings the mapper dropped: `dropped` > 0, with the count, written by `collect`
- [x] Replay age: any `cache == replay`, with the oldest `fetched_at` and the number of live calls during replay, written by `collect`
- [x] Jev degraded: any `llm_fallback` or `truncated` verdict, one per Attempt with the count and keys, written by `relevance`
- [x] Old data: over half of the Sample is older than 30 days, measured from the newest `fetched_at` and never from today, as a closing Caveat
- [x] Broadened: any `broaden` ran, with the count and what changed, as a closing Caveat
- [x] Too few Postings: the Sample is below target, as a closing Caveat
- [x] `_closing_caveats` runs once, when Collection finishes: in `relevance` when Sufficient and in `low_data_review` when passing through
- [x] Test: a normal L2 read raises no Caveat
- [x] Test: Caveat text doesn't change with the clock

Live smoke (a script, not in CI):

- [x] It spends a few Adzuna calls, so get the user's OK in chat before running it
- [x] "Data Analyst, Bangalore" runs through the real models and Adzuna to a Sample, with the route visible in the Run log
- [x] Records whether the 0.5 relevance cut holds and whether 1.5× raw reaches the target in one Attempt
- [x] Any change to the cut or the prompts is noted for the write-up

## Live smoke result ("Data Analyst, Bangalore", minimax-m3.1-flash, real Adzuna)

- Plan target was 100. Attempt 1 gathered 98 raw (1.5x = 150), so 1.5x raw did **not** reach the target in one Attempt: the cap of 6 searches yielded fewer Postings than the goal. 88 of 98 relevant, still short of 100, so it broadened twice. Third Attempt: 220 raw, 138 relevant, Sufficient.
- The 0.5 cut held: 63% relevant overall (90% on Attempt 1). Rejections looked right (accounting, tax and data-centre "analysts"), except "Business Data Analyst", which is borderline.
- No change to the cut or the prompts.
- Jev degraded via `llm_fallback` has no test: `make_deps` has no fallback chain. The `truncated` path is tested.
- Script: `scripts/smoke_collection.py`.
