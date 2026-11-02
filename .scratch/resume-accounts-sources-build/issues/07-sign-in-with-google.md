# 07: Sign in with Google

**What to build:** A CSM on `allowed_emails` signs in with Google, stays signed in for 30 days and can log out. Anyone else, and any signed-out visitor, sees only the sign-in screen. [Accounts and sign-in](../../resume-accounts-sources/issues/14-accounts-and-sign-in.md) is the spec, using the cookie design ticket 05 names.

**Blocked by:** 05: Test the Vercel rewrite on a preview deployment; 06: Runs survive a restart

**Status:** done

- [x] `csms` and `sessions` tables exist; only the SHA-256 of a session token is stored
- [x] All four endpoints work as ticket 14 sets out: `GET /api/auth/google`, its callback, `GET /api/me` and `POST /api/auth/logout`
- [x] The flow is a server-side code exchange with a short-lived `state` cookie, and `email_verified` is required
- [x] `current_csm` guards every `/api` route except `/api/meta` and sign-in, refusing with 401 `signed_out`, and the `Origin` check stays on writes
- [x] `allowed_emails` replaces the access code, is checked at sign-in and on every request, and removal deletes that CSM's sessions but keeps their data
- [x] Failures redirect with `not_allowed`, `unverified_email`, `bad_state` or `google_failed`, and the screen shows a plain message for each
- [x] The SPA sends any 401 to the sign-in card; log out and the CSM's email sit at the foot of the sidebar
- [x] With `database_url` unset, the CLI and local `scout web` stay login-free
- [x] Tests fake Google with `httpx` and cover each failure code, expiry, logout and removal mid-session

**Built with:** the `__Host-session` cookie behind a same-origin `/api`, assumed because ticket 05 hasn't been run. The Vercel rewrite itself is not added, and the cookie design needs re-checking when 05 reports.
