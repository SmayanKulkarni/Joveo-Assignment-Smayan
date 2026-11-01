# Research: signing in across Vercel and Render

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

How should the SPA on Vercel prove who the user is to the API on Render, including on the `EventSource` stream?

- The two are different sites, because `vercel.app` and `onrender.com` are both on the Public Suffix List. Does a `SameSite=None; Secure; HttpOnly` session cookie still work in current Chrome, Firefox and Safari, given their third-party cookie limits? What about CHIPS (`Partitioned`)?
- `EventSource` can send cookies (`withCredentials`) but no headers. Compare a cookie, a short-lived token in the stream URL, and a fetch-based stream reader. Note the security cost of each (tokens in logs, CSRF).
- Proxying `/api` through a Vercel rewrite would make it first-party. [Serving the SPA from Vercel](../../deployment/issues/02-research-vercel-spa-and-cross-origin-sse.md) found SSE through a rewrite undocumented, so check again and test it if possible.
- What CSRF protection each option needs on POSTs, and how it sits with today's access-code `write_guard` and CORS in `clients/web.py`.
- Password hashing on the pinned stack: `argon2-cffi` or `pwdlib` versus `bcrypt`, and whether FastAPI's docs now recommend one.

Capture findings in this ticket's Answer, with long notes in `../assets/`.

## Answer

Researched 2026-11-02. Full notes, with every source: [research-cross-site-sign-in.md](../assets/research-cross-site-sign-in.md).

### Recommendation

- **Proxy `/api` through a Vercel external rewrite** (`/api/:path*` to the Render service, placed before the SPA catch-all). The API becomes first-party, so the session is a plain `__Host-session; Secure; HttpOnly; SameSite=Lax; Path=/` cookie, and `EventSource` sends it with no options and no CORS. The SPA needs no code change, because an unset `VITE_API_URL` already means `/api`.
- **Before relying on it, test SSE through the rewrite on a preview deployment.** Buffering is still undocumented. Also set `x-vercel-enable-rewrite-caching: 0` on `/api/:path*`.
- **Fallback if the rewrite buffers:** call Render directly with `SameSite=None; Secure; HttpOnly; Partitioned`, `allow_credentials=True` in CORS, `credentials: "include"` and `EventSource(url, { withCredentials: true })`. Safari older than 26.2 stays signed out.
- **Don't use** a token in the SSE URL (it ends up in logs and breaks `EventSource` reconnects). Use a bearer token with a fetch-based reader only if cookies fail everywhere.
- **CSRF:** keep the `Origin` check in `write_guard` under every option. With option A, `SameSite=Lax` adds defense in depth.
- **Hash passwords with `pwdlib[argon2]`** and `PasswordHash.recommended()`, plus the FastAPI `DUMMY_HASH` check for unknown emails.

### Key findings

- `vercel.app` and `onrender.com` are both on the [Public Suffix List](https://publicsuffix.org/list/public_suffix_list.dat), so any API cookie is third-party under direct calls.
- **Chrome** still allows third-party cookies by default ([Privacy Sandbox, 2025-04-22](https://privacysandbox.google.com/blog/privacy-sandbox-next-steps)). It blocks them in Incognito or when the user opts in ([MDN](https://developer.mozilla.org/en-US/docs/Web/Privacy/Guides/Third-party_cookies)). `Partitioned` cookies still work when blocking is on ([Chrome CHIPS](https://privacysandbox.google.com/cookies/chips)).
- **Firefox** partitions every third-party cookie by top-level site, in all modes since Firefox 103 ([MDN State Partitioning](https://developer.mozilla.org/en-US/docs/Web/Privacy/Guides/State_Partitioning)). A cookie from a direct call still returns to the SPA.
- **Safari** has blocked all third-party cookies since 2020 ([WebKit](https://webkit.org/blog/10218/full-third-party-cookie-blocking-and-more/)). CHIPS shipped in 18.4, was pulled in 18.5 ([WebKit bug 292975](https://bugs.webkit.org/show_bug.cgi?id=292975)) and came back in Safari 26.2 ([release notes](https://developer.apple.com/documentation/safari-release-notes/safari-26_2-release-notes)). MDN marks CHIPS Baseline since December 2025 ([MDN CHIPS](https://developer.mozilla.org/en-US/docs/Web/Privacy/Guides/Third-party_cookies/Partitioned_cookies)).
- **CORS doesn't override cookie policy.** Credentialed requests need `Access-Control-Allow-Credentials: true` and an explicit origin ([MDN CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS)). `EventSource` takes only `withCredentials`, and it can't send headers ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/EventSource/EventSource)).
- **Vercel's 120-second proxy timeout** applies to first byte and idle gaps, not total duration. The backend can run longer "as long as it continues sending data at least once every 120 seconds" ([changelog](https://vercel.com/changelog/cdn-origin-timeout-increased-to-two-minutes), [limits](https://vercel.com/docs/limits)). FastAPI 0.162's `EventSourceResponse` pings every 15 s and sends `Cache-Control: no-cache` and `X-Accel-Buffering: no`. Render's free cold start takes about a minute ([Render](https://render.com/docs/free)), which is under the limit.
- **Vercel caches external rewrites** for projects created on or after 2026-04-06 when the upstream sends caching headers. Vercel also documents a secret-header transform that stops traffic from bypassing the proxy ([Rewrites](https://vercel.com/docs/routing/rewrites)).
- **CSRF:** OWASP says SameSite "does not replace a proper CSRF defense". It calls Origin verification mandatory, and a required custom header works because it "relies on the CORS preflight mechanism" ([OWASP CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)). OWASP also advises against session IDs in URLs, because of history, the Referer header and logs ([OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)).
- **FastAPI's tutorial uses `pwdlib[argon2]`**. It keeps passlib for legacy hashes only ([FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)). pwdlib 0.3.1 came out on 2026-08-12 ([PyPI](https://pypi.org/pypi/pwdlib/json)). bcrypt 5.0 calls itself "acceptable... but you should really use argon2id or scrypt", and it now rejects passwords over 72 bytes ([PyPI](https://pypi.org/project/bcrypt/)).

### Not verified

- Whether SSE streams through a Vercel external rewrite without buffering. I couldn't test it, because this ticket may not deploy.
- Which `Host` header Vercel sends to Render (this matters for `TrustedHostMiddleware`), and whether `Origin` and `Set-Cookie` pass through unchanged.
- What the proxy returns while Render shows its spin-up loading page.
- Whether Safari 26.2 sends a CHIPS cookie on a cross-site `fetch` or `EventSource`, as opposed to inside an iframe.
- Whether Firefox release builds honour `Partitioned`. It doesn't matter here, because Firefox partitions third-party cookies anyway.
