# 01: Kernel contract and Request & Plan types

**What to build:** the prefactor that makes the stage easy to add, with no behaviour change. The shared country and category tables live in the Kernel, `HiringRequest` carries a validated country, `SearchPlan` enforces its limits so the LLM, an edit and `broaden` share one set of checks, and the stage's types are filled in. Spec: [Request & Plan LLD](../../../docs/lld/request-plan.md) §3, §6, §11, §12 pass 1 steps 1-2 (the `runtime/graph.py` edge changes belong to tickets 02 and 03).

**Blocked by:** None (can start immediately).

**Status:** done

- [x] `ADZUNA_CURRENCY` moves to the Kernel and `ADZUNA_CATEGORIES` is added, with the Gateway re-using both
- [x] `HiringRequest.country` is required and must be in `ADZUNA_CURRENCY`, and existing fixtures and stubs are updated
- [x] `SearchPlan` enforces the LLD limits on `titles`, `country`, `radius_km`, `max_days_old`, `target_postings` and `category`
- [x] `State` gains `request_draft`, `plan_decision` and `plan_feedback`, owned by Request & Plan
- [x] `default_country` setting exists, defaults to `us` and must be in `ADZUNA_CURRENCY`
- [x] `RequestDraft` is added with every field nullable, and `PlanReviewAnswer` requires `plan` on edit and `feedback` on reject
- [x] Test: each limit rejects its bad value, and `ADZUNA_CATEGORIES` matches the tags in the USAJOBS domains table
- [x] Test: `PlanReviewAnswer` rejects `edit` with no plan and `reject` with no feedback, and all the models survive the Runtime serde test
- [x] The existing test suite still passes

**Notes:** `check_country` in `kernel/types.py` is the one country check, shared by `HiringRequest`, `SearchPlan` and the `default_country` setting. `RequestDraft` and `WorkMode` are added to `ALLOWED_MSGPACK` so the draft survives the serde test. The `clarify` edge and `clarity_check` targets were already in `runtime/graph.py`. `Fetch` keeps its own country check and message.
