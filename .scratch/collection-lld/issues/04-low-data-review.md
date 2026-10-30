# The low_data_review Pause

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

What does the user see at `low_data_review`, what can they answer, and what does pass 1's pass-through do?

## Answer

Decided by grilling.

- **`LowDataPayload`:** `count`, `target`, `attempts`, the plans tried, how many Postings were fetched and rejected, `calls_left`, and `fetch_blocked`.
- **`LowDataAnswer`:** `action` (`broaden`, `continue`, `abort`) plus optional `guidance`, which feeds the next `broaden`.
- **New slices:** `low_data_decision` and `low_data_guidance`, written by the Pause and read by the router.
- **`broaden` is always allowed and has no cap,** because a human drives each one, the same reasoning as `plan_review` rejects. It can't be refused for lack of quota:
  - The Controller validates an answer without seeing the payload (Runtime §5), so a validator can't know the budget is out.
  - A user returning the next day has fresh quota, while the stored Pause still says it's gone.
  - If quota is still out, the next Attempt finds nothing new and returns to the same Pause, at the cost of one `broaden` call, one `fetch_agent` turn and no quota.
- **`abort`** goes to END. **`continue`** logs a Caveat and goes to analysis.
- **Pass 1:** a pass-through that doesn't interrupt, leaves the decision null, and still logs the Too few Postings Caveat. The router treats null as `continue`.
