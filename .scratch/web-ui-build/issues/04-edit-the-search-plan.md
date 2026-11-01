# 04: Edit the Search Plan

**What to build:** at the plan Pause, a user presses Edit, changes the Search Plan in a proper form, and the Run goes on with the edited plan. A value the server refuses shows under its own field. Spec: [Web UI LLD](../../../docs/lld/web-ui.md) §8 (`PlanEditor`, refusals).

**Blocked by:** 03: Answer a Pause and carry on

**Status:** done

- [ ] The form starts from the Pause's plan and covers all seven fields as §8's table says
- [ ] Titles take 1 to 4 rows, with add and remove
- [ ] Country and category are selects from `/meta`, with category also offering "Any" (null)
- [ ] A blank location means country-wide
- [ ] Number inputs carry the model's limits, but the server stays the check
- [ ] "Use this plan" posts `{action: "edit", plan, feedback: null}`, and the Run continues with that plan
- [ ] An error with `loc[0] === "plan"` shows under the field named by `loc[1]`, and anything else at the top of the card, with values kept
- [ ] Cancelling the edit returns to the read view with no request sent
- [ ] Checked by hand through a Demo Run: a refused edit (with HTML limits bypassed), a corrected one, and the edited plan visible in the Brief's Run Notes
