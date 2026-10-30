# Who builds the Sends

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

`relevance`'s router must return `Send` × N to `batch_extract`, but the payload and batching belong to Analysis, and a stage may import only `runtime/deps.py` and `runtime/pause.py`. Who builds them?

## Answer

Decided by grilling.

- **Collection's routers return a plain `"analyse"` outcome,** and `runtime/graph.py` turns it into `analysis.fan_out(state)`.
- **`fan_out` also sends zero Postings to `stats`,** which moves the HLD's "continue with 0 postings" edge case out of Collection.
- This changes the `CONDITIONAL` handling in Runtime §4 slightly. ⏳ The Analysis LLD owns `fan_out`'s body.
