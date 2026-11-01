# 03: Answer a Pause and carry on

**What to build:** a user answers each Pause in an inline card and the Run continues on the same page, so a Demo Run goes from request to its end. Bad answers show against the same card with nothing changed. Spec: [Web UI LLD](../../../docs/lld/web-ui.md) §4 (resume, refusals), §7 (Connecting, the base after answering), §8.

**Blocked by:** 02: Start a Run and watch it reach a Pause

**Status:** done

Scope limits, each lifted by a later ticket:
- `plan_review` offers Approve, Ask for a different plan, and Abort. The Edit button is 04.
- The end of a Run shows a plain "Done" or "Aborted" line. The Brief is 05.
- A reopened paused Run renders its card, but its earlier history is 08.

- [ ] `POST /api/runs/{id}/resume` works, with `InvalidAnswer` cleaned to `{loc, msg}` and its "Value error, " prefix stripped
- [ ] `clarify`: option chips are real radio inputs, a chip fills the box and typing clears the chip, blank is a skip, and the answers stay in question order
- [ ] The clarify button reads "Continue without answering" when all are blank
- [ ] `plan_review` shows the Search Plan and Assumptions readably, with no field names
- [ ] `low_data_review` shows the counts, any block reason, calls left and the plans tried, with optional guidance feeding Search wider
- [ ] Every action posts the exact payload in §8's table, with all of `PlanReviewAnswer`'s keys
- [ ] Abort is two-step on both cards
- [ ] A refused answer keeps the values and the card, and leaves the Run `paused`
- [ ] `run_locked` retries once after 300 ms, then shows "This Run is open elsewhere"
- [ ] `not_resumable`, or an answer the Run isn't waiting for, shows "Answered elsewhere" and rebuilds from `RunDetail`
- [ ] `balance_too_low` and `upstream` show their message and the Run can be retried
- [ ] After answering, the card collapses to a one-line record, the Step leaves waiting, and a new stream opens with the state on screen as its base
- [ ] Every refusal and payload is covered in `pytest`
- [ ] Checked by hand through a Demo Run, all three Pauses to `done`, plus an abort of each kind
