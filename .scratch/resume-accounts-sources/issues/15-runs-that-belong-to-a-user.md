# Runs that belong to a user

Type: grilling
Status: open
Assignee: none
Blocked by: [Accounts and sign-in](14-accounts-and-sign-in.md)

## Question

How does every Run come to belong to exactly one user, and what does that change in the Controller, registry and API?

- Where the owner is stored: a column in the `runs` registry, the thread config, or both. Who checks it: the API layer only, or the Controller too.
- Every endpoint in `clients/web.py` (list, get, start, resume, cancel, events, brief download) refuses another user's Run. Should it refuse with 404 or 403?
- What happens to Runs that already exist, and to Demo Runs and the seeded Runs in `runtime/seed.py`: owned by nobody and hidden, shown to everyone, or given to a seed account.
- Quota across users: the daily Adzuna guard is global today. Does each user get a share or a daily Run cap, or does the global guard stay the only limit?
- The concurrent-resume guard and the live `RunHandle` re-attach (`attached`) when the same user has two tabs open, and when a different user tries the same thread ID.
- The Runtime and Web UI LLD sections to update.

Load `langchain-router` if the owner goes into the thread config or the Store.
