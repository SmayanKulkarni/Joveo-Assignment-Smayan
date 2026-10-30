# 04: Search Plan and the pass-through `plan_review`

**What to build:** a final `hiring_request` becomes a `search_plan` within the limits, written by the strong tier, and the Run carries on to `fetch_agent` through a pass-through `plan_review`. Spec: [Request & Plan LLD](../../../docs/lld/request-plan.md) §4, §6, §7, §9, §12 pass 1 steps 6-7.

**Blocked by:** 02: A clear request reaches `plan`.

**Status:** done

- [x] `plan` uses the strong tier with `SearchPlan` directly, and writes `search_plan` and one `note` with the titles and target
- [x] Its input is `hiring_request` and the Assumptions, plus the previous plan and `plan_feedback` when `plan_decision` is `reject`, and it does not read `focus`
- [x] `PLAN_SYSTEM` follows the rules in §7
- [x] `make_nodes` exports `plan_review` as a pass-through returning `{}`, so `plan_decision` stays null
- [x] `after_review` reads only state: `abort` goes to END, `reject` to `plan`, and anything else, including null, to `fetch_agent`
- [x] Test with fake chains: a bad plan then a good one passes on the feedback retry
- [x] Test: all `after_review` outcomes
- [x] Graph test with other stages stubbed: a clear request reaches `fetch_agent` with a `search_plan` set

**Notes:** `plan_review` is now the real Pause from ticket 06, so the stage graph tests assert the plan reaches `plan_review` and then `fetch_agent`.
