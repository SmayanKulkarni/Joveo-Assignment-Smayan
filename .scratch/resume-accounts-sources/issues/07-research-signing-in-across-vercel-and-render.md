# Research: signing in across Vercel and Render

Type: research
Status: open
Assignee: none
Blocked by: none

## Question

How should the SPA on Vercel prove who the user is to the API on Render, including on the `EventSource` stream?

- The two are different sites, because `vercel.app` and `onrender.com` are both on the Public Suffix List. Does a `SameSite=None; Secure; HttpOnly` session cookie still work in current Chrome, Firefox and Safari, given their third-party cookie limits? What about CHIPS (`Partitioned`)?
- `EventSource` can send cookies (`withCredentials`) but no headers. Compare a cookie, a short-lived token in the stream URL, and a fetch-based stream reader. Note the security cost of each (tokens in logs, CSRF).
- Proxying `/api` through a Vercel rewrite would make it first-party. [Serving the SPA from Vercel](../../deployment/issues/02-research-vercel-spa-and-cross-origin-sse.md) found SSE through a rewrite undocumented, so check again and test it if possible.
- What CSRF protection each option needs on POSTs, and how it sits with today's access-code `write_guard` and CORS in `clients/web.py`.
- Password hashing on the pinned stack: `argon2-cffi` or `pwdlib` versus `bcrypt`, and whether FastAPI's docs now recommend one.

Capture findings in this ticket's Answer, with long notes in `../assets/`.
