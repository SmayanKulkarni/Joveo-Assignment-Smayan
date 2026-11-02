# Runs that belong to a Customer

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [Customers and what a CSM can do with them](26-customers-and-what-a-csm-can-do-with-them.md)

## Question

How does every Run come to belong to exactly one Customer, and so to that Customer's CSM, and what does that change in the Controller, registry and API?

- A Run can't start without a Customer, Market Brief Runs included. Can a Run be moved to another Customer if the CSM picked the wrong one?
- Where the owner is stored: a column in the `runs` registry, the thread config, or both. Who checks it: the API layer only, or the Controller too.
- Every endpoint in `clients/web.py` (list, get, start, resume, cancel, events, brief download) refuses another CSM's Run. Should it refuse with 404 or 403?
- What happens to Runs that already exist, and to Demo Runs and the seeded Runs in `runtime/seed.py`: owned by nobody and hidden, shown to everyone, or given to a seed account.
- Quota across users: the daily Adzuna guard is global today. Does each CSM get a share or a daily Run cap, or does the global guard stay the only limit?
- The concurrent-resume guard and the live `RunHandle` re-attach (`attached`) when the same CSM has two tabs open, and when a different CSM tries the same thread ID.
- The Runtime and Web UI LLD sections to update.

Load `langchain-router` if the owner goes into the thread config or the Store.

## Answer

Decided by the agent alone on 2026-11-02, at the user's request, with no grilling. The decisions are in [Final decisions](../final-decisions.md#runs-that-belong-to-a-customer).
