# 13: Customer Profile

**What to build:** A Customer's Profile tab shows what was learned from their finished Runs, how many Runs each value came from, and their earlier results. The CSM can set or remove a value or clear the lot. It doesn't change any Run yet. [What a Customer Profile holds](../../resume-accounts-sources/final-decisions.md#what-a-customer-profile-holds) is the spec.

**Blocked by:** 09: Runs belong to a Customer

**Status:** done (see commit)

- [x] A `customer_profiles` table holds JSON `learned`, `pinned` and `removed`, plus `cleared_at`; the LangGraph Store isn't used
- [x] Code recomputes `learned` from the last 10 Done Runs when a Run reaches Done or is deleted; a failure is logged and doesn't fail the Run
- [x] Only the kept fields are learned, each taking its commonest value with ties to the newest, and cancelled or stopped Runs don't count
- [x] No LLM reads or writes the profile, and no model-written free text is stored
- [x] `pinned` beats learned, `removed` is never relearned, and clearing ignores Runs before `cleared_at`
- [x] `GET`, `PATCH` and `DELETE /api/customers/{id}/profile` work, and another CSM's gets 404
- [x] Deleting a Customer now also removes their profile
- [x] Tests cover the window, ties, pin, remove, clear, a Run deleted, and recomputing from pruned Runs
