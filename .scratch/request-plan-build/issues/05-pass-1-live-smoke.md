# 05: Pass 1 live smoke

**What to build:** a script (not in CI) runs the spec's cases through the real models, proving the stage behaves on real output. This is the first real check of the 0.5 clarity cut, and of both chain models accepting the `SearchPlan` limits under strict `json_schema`. Spec: [Request & Plan LLD](../../../docs/lld/request-plan.md) §12 pass 1 step 8.

**Blocked by:** 03: The clarify loop, re-ask cap and settling; 04: Search Plan and the pass-through `plan_review`.

**Status:** done

- [x] "Data Analyst, Bangalore" asks nothing and gives a valid `search_plan`
- [x] "Engineer, Texas" asks, and gives a valid `search_plan` once answered
- [x] Both chain models accept the new `maximum` and `maxItems` keywords under strict `json_schema`, or the limits move into a `model_validator` that leaves them out of the schema
- [x] Any change to the clarity cut or the prompts is noted for the write-up

**Notes:** `scripts/smoke_request_plan.py [model]` ran on both chain models, `minimax/minimax-m3.1-flash` and `deepseek/deepseek-v4.1-flash`, each pinned for both tiers. Both accepted the `maximum` and `maxItems` limits under strict `json_schema`, so no `model_validator` move was needed. `scripts/smoke_cli.py` now answers by prompt and ran `scout run "Engineer, Texas"` end to end through the real Controller and CLI to `done` with exit code 0, including the real `plan_review`. Findings for the write-up: (1) Jev at the 0.5 cut kept rating "Texas" and even "Austin, Texas" as ambiguous after the user answered, so `location` settled with an Assumption after two asks on both models; the clarity cut looks too eager for `location`. (2) The question writer put numbered options in the question text, fixed in `QUESTION_SYSTEM`. (3) The plan added Junior and level-number titles with no seniority stated, fixed in `PLAN_SYSTEM` and gone on the deepseek re-run.
