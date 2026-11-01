# Accounts and sign-in

Type: grilling
Status: open
Assignee: none
Blocked by: [Research: durable storage for accounts and Runs](06-research-durable-storage-for-accounts-and-runs.md), [Research: signing in across Vercel and Render](07-research-signing-in-across-vercel-and-render.md)

## Question

How do sign-up, login and logout work, and where do accounts live?

- What an account holds: email, password hash, created time, and anything else. Email rules (case, uniqueness), and password rules.
- Session mechanism, from the research: cookie, token, or a proxy that makes the API first-party. How long a session lasts, and logout.
- Hand-rolled with `pwdlib` or `argon2` and a sessions table, or a library such as `fastapi-users`. Pick the smaller one that is still safe.
- Rate limiting of login and sign-up attempts, at the smallest level that stops brute force.
- Whether the shared access code goes away, stays as a sign-up gate (an invite code), or stays beside accounts.
- The CLI: does `scout` stay single-user and local with no login, or does it sign in too?
- Where the tables live, from [Research: durable storage for accounts and Runs](06-research-durable-storage-for-accounts-and-runs.md), and how they're created and migrated.
- Endpoints and their refusals, written in the style of the Web UI LLD's API section.
