# Accounts and sign-in

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [Research: durable storage for accounts and Runs](06-research-durable-storage-for-accounts-and-runs.md), [Research: signing in across Vercel and Render](07-research-signing-in-across-vercel-and-render.md)

## Question

How does a CSM sign up, log in and log out, and where do those accounts live? Customers never sign in; they are records a CSM keeps, decided in [Customers and what a CSM can do with them](26-customers-and-what-a-csm-can-do-with-them.md).

- What an account holds: email, password hash, created time, and anything else. Email rules (case, uniqueness), and password rules.
- Session mechanism, from the research: cookie, token, or a proxy that makes the API first-party. How long a session lasts, and logout.
- Hand-rolled with `pwdlib` or `argon2` and a sessions table, or a library such as `fastapi-users`. Pick the smaller one that is still safe.
- Rate limiting of login and sign-up attempts, at the smallest level that stops brute force.
- Whether the shared access code goes away, stays as a sign-up gate (an invite code), or stays beside accounts.
- The CLI: does `scout` stay single-user and local with no login, or does it sign in too?
- Who may become a CSM: since this is now a staff tool, whether the invite code is enough, or whether email domains are restricted too.
- Where the tables live, from [Research: durable storage for accounts and Runs](06-research-durable-storage-for-accounts-and-runs.md), and how they're created and migrated.
- Endpoints and their refusals, written in the style of the Web UI LLD's API section.

## Answer

Grilled with the user on 2026-11-02. The user accepted every recommendation, after choosing Google over passwords and declining Neon's own auth, which would need a token its JWTs can't deliver to `EventSource`.

- Sign in with Google only, no passwords. Customers and all other mappings stay in our own tables, keyed on our own CSM `id`.
- Proxy `/api` through a Vercel rewrite with a `__Host-session` cookie, with a task ticket to test it on a preview deployment before the LLD is written. The fallback is a `Partitioned` cookie on direct calls.
- `allowed_emails` lists who may sign in, replacing the access code. It is checked at sign-in and on every request.
- Sessions are random opaque tokens, with only the SHA-256 stored in a `sessions` table, lasting a fixed 30 days. Logout deletes the row and clears the cookie. Expired rows are removed at sign-in.
- The CLI and a local `scout web` stay login-free. `database_url` set means Postgres and sign-in; unset means SQLite and no sign-in. The service refuses to start on Render when it's unset.
- `csms` and `sessions` live in Neon, created by idempotent `CREATE TABLE IF NOT EXISTS` at startup beside the checkpointer's `setup()`, with no Alembic and a `ponytail:` comment naming the ceiling.
- A `csms` row holds `id` (UUID), `google_sub` (unique), `email` and `created_at`. The flow is a server-side authorization code exchange through `httpx`, scope `openid email`, a short-lived `state` cookie, and `email_verified` required. The email is refreshed at each sign-in and compared lowercased. No password library or login rate limits.
- **Endpoints:** `GET /api/auth/google` sets the `state` cookie and redirects to Google. `GET /api/auth/google/callback` checks `state`, exchanges the code, checks the email, finds or creates the `csms` row, sets the session cookie and redirects to `/`. `GET /api/me` returns `{id, email}`, or 401 when signed out. `POST /api/auth/logout` deletes the session, clears the cookie and returns 204. The Google redirect URL is built from `web_origin`. New settings: `google_client_id`, `google_client_secret`, `allowed_emails`.
- **Failed sign-in:** every failure redirects to `/?signin=<code>` and sets no session. Codes: `not_allowed`, `unverified_email`, `bad_state`, `google_failed`.
- **What needs a session:** a `current_csm` dependency guards every `/api` route except `/api/meta` and the sign-in routes, refusing with 401 `signed_out`. Reads are no longer open. The `Origin` check stays on every POST. The SPA sends a 401 to the sign-in screen. Access to a particular Run belongs to [Runs that belong to a Customer](15-runs-that-belong-to-a-customer.md).
- **Removed mid-session:** a CSM no longer in `allowed_emails` gets the same 401 and their session rows are deleted. Their `csms` row and Customers stay, so adding them back restores everything. A Run already streaming keeps going, because `/events` checks only when it connects.
- **Ceiling:** with no Alembic, changes to existing columns are hand-written `ALTER`s in the startup script.

The rewrite test is in [Test SSE and sign-in through the Vercel rewrite](29-test-sse-and-sign-in-through-the-vercel-rewrite.md).
