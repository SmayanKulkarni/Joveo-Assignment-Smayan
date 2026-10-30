# 06: Real `plan_review` and the `salary` alias

**What to build:** pass 2. A user sees the Search Plan and Assumptions before any quota is spent, and can approve, edit, reject with feedback or abort. `--focus salary` is accepted as an alias for `compensation`. Spec: [Request & Plan LLD](../../../docs/lld/request-plan.md) §6 (`plan_review`), §8, §12 pass 2.

**Blocked by:** 04: Search Plan and the pass-through `plan_review`; Runtime build 03: CLI and `--focus`.

**Status:** done

- [x] `plan_review` pauses with `PlanReviewPayload(plan, assumptions)`, and writes `plan_decision`, `plan_feedback` and a `pause` log entry
- [x] An `edit` replaces `search_plan` with the user's plan
- [x] Rejects have no cap
- [x] Test: approve, edit, reject with feedback reaching the next `plan`, abort, and a bad edit re-prompting
- [x] Test: `--focus salary` lands in the checkpoint as `compensation`

**Notes:** the `salary` alias was already in the CLI from Runtime build 03, with its checkpoint test in `tests/test_cli.py`. A bad edit is refused by `PlanReviewAnswer` validation before it reaches the node, which is what the CLI re-prompts on.
