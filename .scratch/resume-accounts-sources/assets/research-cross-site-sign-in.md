# Research: signing in across Vercel and Render

Researched 2026-11-02 for [ticket 07](../issues/07-research-signing-in-across-vercel-and-render.md). Sources are primary (browser vendors, MDN, Vercel, Render, FastAPI, OWASP, PyPI) unless marked. Nothing was deployed, so nothing here was tested live.

## The setup today

- The SPA calls `${VITE_API_URL}/api` (`web/src/api/client.ts`). With `VITE_API_URL` unset, it already calls same-origin `/api`.
- `web/src/api/stream.ts` opens `new EventSource(`${API}/runs/${id}/events`)` with no options, and relies on the browser's automatic reconnect plus a 204 to stop it.
- `write_guard` in `src/talent_scout/clients/web.py` refuses a POST whose `Origin` is neither `web_origin` nor the request's own host, then checks `X-Access-Code`. GETs are open.
- `CORSMiddleware` allows only `web_origin`, methods GET and POST, headers `Content-Type` and `X-Access-Code`, and no credentials.
- FastAPI 0.162.0's `EventSourceResponse` sets `Cache-Control: no-cache` and `X-Accel-Buffering: no`, and sends a `: ping` comment every 15 seconds when the generator is idle (`.venv/Lib/site-packages/fastapi/routing.py` around line 682, `fastapi/sse.py` `_PING_INTERVAL = 15.0`).

## Why the two hosts are different sites

Both `vercel.app` and `onrender.com` are entries in the [Public Suffix List](https://publicsuffix.org/list/public_suffix_list.dat) (checked 2026-11-02, lines 16327 and 15556). So `x.vercel.app` and `y.onrender.com` are each their own registrable site, and a cookie set by the API while the user is on the SPA is a third-party cookie.

## Third-party cookie rules, late 2026

| Browser | Unpartitioned `SameSite=None` cookie on a cross-site fetch | `Partitioned` (CHIPS) cookie |
|---|---|---|
| Chrome | Sent by default. Blocked in Incognito and when the user blocks third-party cookies. | Supported since Chrome 114. Still allowed when third-party cookies are blocked. |
| Firefox | Not blocked, but partitioned by top-level site in every mode since Firefox 103. A cookie the API sets while on the SPA comes back on later requests from the SPA. | Firefox partitions everything anyway, so the attribute changes little. CHIPS status in Firefox is unclear (see Not verified). |
| Safari | Blocked. Full third-party cookie blocking since Safari 13.1 (March 2020). | Shipped in 18.4, pulled in 18.5 for a bug, back in Safari 26.2 (December 2025). |

Sources:

- Chrome kept third-party cookies on by default and dropped the planned prompt: "we've made the decision to maintain our current approach to offering users third-party cookie choice in Chrome" ([Privacy Sandbox blog, 2025-04-22](https://privacysandbox.google.com/blog/privacy-sandbox-next-steps)). MDN: Chrome blocks them "only in Incognito mode, or when users explicitly set it" ([MDN, Third-party cookies](https://developer.mozilla.org/en-US/docs/Web/Privacy/Guides/Third-party_cookies)).
- CHIPS: partition key is the top-level site, `Secure` is required, `__Host-` is recommended, and when third-party cookies are blocked a site "will only be able to set and access the cookie with the `Partitioned` attribute" ([Chrome, CHIPS](https://privacysandbox.google.com/cookies/chips)). MDN marks CHIPS "Baseline 2025... Since December 2025, this feature works across the latest devices and browser versions" ([MDN, CHIPS](https://developer.mozilla.org/en-US/docs/Web/Privacy/Guides/Third-party_cookies/Partitioned_cookies)).
- Firefox: "Firefox provides embedded resources with a separate storage bucket for every top-level website", "Enabled by default for all users since Firefox 103" ([MDN, State Partitioning](https://developer.mozilla.org/en-US/docs/Web/Privacy/Guides/State_Partitioning)).
- Safari: "Cookies for cross-site resources are now blocked by default across the board" ([WebKit blog, 2020-03-24](https://webkit.org/blog/10218/full-third-party-cookie-blocking-and-more/)). CHIPS history in [WebKit bug 292975](https://bugs.webkit.org/show_bug.cgi?id=292975). Safari 26.2 release notes, Privacy: "Added support for Cookies Having Independent Partitioned State (CHIPS)" ([Apple](https://developer.apple.com/documentation/safari-release-notes/safari-26_2-release-notes)).
- CORS does not override any of this: "Cookies set in CORS requests and responses are subject to normal third-party cookie policies" ([MDN, CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS)).

So a plain `SameSite=None; Secure; HttpOnly` cookie fails in every Safari and in Chrome Incognito. Adding `Partitioned` makes it work in current Chrome, Firefox and Safari 26.2+, and still fails on any Safari older than 26.2 (iPhones that haven't updated). The partition is keyed to the SPA's site, which is exactly the one site that needs it, so partitioning costs nothing here.

## The four options

### A. Proxy `/api` through a Vercel rewrite (first-party cookie)

`vercel.json` gets `{ "source": "/api/:path*", "destination": "https://<service>.onrender.com/api/:path*" }` ahead of the SPA catch-all. The browser then sees one origin, so:

- The session cookie is `__Host-session=<random>; Secure; HttpOnly; SameSite=Lax; Path=/`, a plain first-party cookie that every browser accepts.
- `EventSource` is same-origin and sends the cookie with no options. No CORS at all.
- The SPA needs no code change: `VITE_API_URL` unset already gives `/api`.

What Vercel documents about external rewrites ([Rewrites, updated 2026-08-11](https://vercel.com/docs/routing/rewrites); [Limits, updated 2026-09-16](https://vercel.com/docs/limits); [changelog 2025-05-08](https://vercel.com/changelog/cdn-origin-timeout-increased-to-two-minutes)):

- Proxied request timeout is 120 seconds on every plan. The changelog says what it measures: Vercel "will now wait up to 120 seconds for your backend to start sending data", and the backend can run longer "as long as it continues sending data at least once every 120 seconds". That is a first-byte and idle-gap limit, not a total-duration limit. This is new since the [deployment research](../../deployment/issues/02-research-vercel-spa-and-cross-origin-sse.md), which found total duration undocumented.
- FastAPI pings every 15 seconds, so idle gaps never reach 120 seconds. Render's free cold start takes "about one minute" ([Render, Free](https://render.com/docs/free)), which is under the first-byte limit but not by much.
- Vercel forwards `x-forwarded-for`, `x-real-ip`, `x-forwarded-host`, `x-forwarded-proto`.
- Projects created on or after 2026-04-06 cache external rewrite responses when the upstream sends caching headers. SSE sends `no-cache`. Setting `x-vercel-enable-rewrite-caching: 0` on `/api/:path*` turns rewrite caching off entirely and is the cheap safe choice.
- Vercel documents a way to stop people bypassing the proxy: a `routes` transform that sets a secret header, checked at the origin with a timing-safe compare. Optional here.
- Buffering of a streamed response is still not documented anywhere I found. The docs never mention SSE or streaming for rewrites.

CSRF: the cookie is `SameSite=Lax`, so a foreign site's POST arrives without it. Keep the existing `Origin` check in `write_guard` as the real defense, which OWASP calls for alongside SameSite ("useful as a defense-in-depth control but it does not replace a proper CSRF defense", [OWASP CSRF cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)). Through the proxy, the browser's `Origin` is the Vercel origin, which equals `web_origin`, so the check passes unchanged. `Sec-Fetch-Site: same-origin` ([MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Sec-Fetch-Site)) could be added, but OWASP says origin verification stays mandatory beside it, and we already have that.

Costs: one more hop on every request, the API's real host is still public unless the secret header is added, and SSE streaming through the proxy must be tested before relying on it.

### B. Direct cross-site with a `Partitioned` cookie

Cookie `__Host-session=<random>; Secure; HttpOnly; SameSite=None; Path=/; Partitioned`. `CORSMiddleware(allow_credentials=True)` with the single `web_origin`, `fetch(..., { credentials: "include" })`, and `new EventSource(url, { withCredentials: true })` ([MDN, EventSource()](https://developer.mozilla.org/en-US/docs/Web/API/EventSource/EventSource)). Credentialed CORS needs `Access-Control-Allow-Credentials: true` and an explicit origin, never `*` ([MDN, CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS)).

Works in Chrome (even with third-party cookies blocked), Firefox, and Safari 26.2+. Fails on older Safari. CSRF: `SameSite=None` means the browser sends the cookie on any cross-site request, so the `Origin` check is mandatory, plus a required custom header (or JSON body) that forces a CORS preflight, which OWASP lists as a defense that "relies on the CORS preflight mechanism". `write_guard` already does the `Origin` part.

### C. Short-lived token in the SSE URL

An authenticated POST mints a ticket, and the SPA opens `EventSource(`/runs/${id}/events?ticket=...`)`. Costs:

- URLs land in Render's and any proxy's request logs, browser history and `Referer`. OWASP: IDs in URLs "might disclose the session ID" through history, bookmarks and the Referer header, and advises accepting session IDs only from cookies ([OWASP Session Management cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)).
- `EventSource` reconnects to the same URL by itself. `stream.ts` relies on that. A single-use or 60-second ticket breaks every reconnect, and a ticket that lives as long as the stream is close to a session token in the URL.
- No CSRF exposure on the stream itself (a GET that only reads), and the POSTs can still use the Authorization header.

Only worth it if cookies are off the table entirely.

### D. Bearer token plus a fetch-based stream reader

Keep the token in memory or `localStorage`, send `Authorization: Bearer` on every fetch (what the [FastAPI OAuth2 tutorial](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) shows), and read the stream with `fetch()` and `response.body.getReader()` so the header can be sent. Costs:

- `stream.ts` loses the browser's reconnect, `Last-Event-ID` and the 204 stop signal for free, and has to rebuild them, about 40 lines plus an SSE line parser.
- Any XSS can read a token from `localStorage`. An `HttpOnly` cookie can't be read by script (OWASP Session Management).
- No CSRF: the browser never attaches the header by itself. The Authorization header forces a preflight, so CORS must allow it.
- Works in every browser regardless of cookie policy.

## How each sits with today's guards

| | `write_guard` Origin check | `X-Access-Code` | `CORSMiddleware` |
|---|---|---|---|
| A. Proxy | Keep as is; Origin is `web_origin` | Accounts can replace it (ticket 14) | Not needed for the SPA; can stay for local dev |
| B. Partitioned cookie | Keep; now mandatory | Same | Add `allow_credentials=True` |
| C. URL ticket | Keep | Same | Unchanged |
| D. Bearer + fetch stream | Keep | Same | Add `Authorization` to `allow_headers` |

`TrustedHostMiddleware` under option A depends on the `Host` header Vercel sends to the origin. If Vercel sends the Render hostname, nothing changes. If it sends the Vercel host, that host must be added (see Not verified).

## Password hashing

- FastAPI's security tutorial now uses pwdlib with Argon2: `uv add "pwdlib[argon2]"`, `password_hash = PasswordHash.recommended()`. pwdlib "also supports the bcrypt hashing algorithm" and points to passlib only for legacy hashes. It also verifies against a `DUMMY_HASH` when the user doesn't exist, so response time doesn't reveal which emails have accounts ([FastAPI, OAuth2 with JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)).
- pwdlib 0.3.1, released 2026-08-12, needs Python 3.10+, and its `argon2` extra pulls `argon2-cffi>=23.1.0` ([PyPI](https://pypi.org/pypi/pwdlib/json)).
- bcrypt 5.0.0 (2025-09-25) describes itself as "Acceptable password hashing (but you should really use argon2id or scrypt)", and since 5.0.0 raises `ValueError` for passwords over 72 bytes instead of truncating ([PyPI, bcrypt](https://pypi.org/project/bcrypt/)).
- So: `pwdlib[argon2]`. Using `argon2-cffi` directly would also work, but pwdlib is what the FastAPI docs show, and it keeps the algorithm choice behind `recommended()`.

Session IDs, whichever transport carries them, need at least 64 bits from a CSPRNG (OWASP Session Management). `secrets.token_urlsafe(32)` covers it.

## Not verified

- Whether a Vercel external rewrite streams SSE without buffering. Not tested, since this ticket may not deploy. Test: deploy the rewrite to a preview, open a Run's events, and check that events arrive one by one, not in a burst at the end.
- Which `Host` header Vercel sends to the origin, and whether it passes `Origin` and `Set-Cookie` through untouched. Expected yes, not documented.
- What the browser gets through the proxy while Render shows its spin-up "loading page". It could be an HTML 200 that the SPA tries to parse as JSON.
- Safari 26.2's CHIPS on a cross-site `fetch` and `EventSource`. Every vendor example uses iframes.
- Whether Firefox honours `Partitioned` in release builds (a Bugzilla note mentions a `network.cookie.CHIPS.enabled` pref). It doesn't matter for this app, because Firefox partitions all third-party cookies anyway.
