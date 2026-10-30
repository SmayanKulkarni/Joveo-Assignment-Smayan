# Pause payloads and answers

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01, 02, 03

## Question

What are the final payload and answer fields for `clarify` and `plan_review`, replacing the stub shapes in Runtime §5?

- How `clarify` matches answers to questions, given the Controller validates without seeing the payload.
- What `plan_review` shows and which answers are invalid.
- Which state fields `plan_review` writes, and how pass 1 behaves before the real Pause exists.

## Answer

Decided by grilling.

- **`ClarifyPayload`:** only the unanswered questions.
- **`ClarifyAnswer(answers: list[str])`:** matched by position. The Controller validates without the payload, so it can't check the count. The node pads missing answers with blanks and drops extras. A blank counts as vague, so Enter skips a question and uses up that field's asks.
- **CLI:** typing a number picks that option, and anything else is free text.
- **`PlanReviewPayload`:** the plan plus the Assumptions, because this is the last moment the user can correct one before quota is spent.
- **`PlanReviewAnswer(action, plan, feedback)`:** validators require `plan` on `edit` and `feedback` on `reject`, so a bad answer re-prompts.
- **New private fields:** `plan_decision` and `plan_feedback`. Rejects have no cap, since a human drives each one.
- **Pass 1:** `plan_review` is a pass-through returning `{}`, and a null `plan_decision` routes to `fetch_agent`.
