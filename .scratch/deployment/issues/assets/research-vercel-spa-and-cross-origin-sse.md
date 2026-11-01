# Research: serving the SPA from Vercel and reaching the backend

Answers ticket [02](../02-research-vercel-spa-and-cross-origin-sse.md). Sources fetched 2026-11-01. The "updated" dates are the `last_updated` values on the Vercel pages.

Each answer is marked **Documented** (a primary source says it) or **Live check** (the docs are silent or unclear, so test it on a real deployment). **Inference** marks a conclusion drawn from documented facts.

## Recommendation for tickets 03 and 05

Call the backend directly from the browser, with CORS on the backend, for the stream at least. Vercel documents a rewrite timeout, but no documented promise covers streaming through a rewrite. A direct call depends only on web standards. The cost is that the `<a download>` links and the relative `/api` paths must change. See section 3 for the comparison.

## 1. Deploying from `web/` with the CLI

**Documented**

- **Vite is a supported preset.** Run `vercel` from the project root ([Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite), updated 2026-08-26).
- **Subdirectory:** either pass `--cwd` ([global options](https://vercel.com/docs/cli/global-options), updated 2026-05-28) or set the project's Root Directory. An app with a Root Directory cannot reach files outside it, and the setting also applies to the CLI, so you then run plain `vercel` ([configure a build](https://vercel.com/docs/builds/configure-a-build), updated 2026-08-28).
- **Non-interactive flags:**
  - `--yes` answers the project setup questions with defaults inferred from `vercel.json` and the folder name.
  - `--prod` deploys to production. The first deployment of a new project is always production.
  - stdout is always the deployment URL, and any non-zero exit code means an error ([vercel deploy](https://vercel.com/docs/cli/deploy), updated 2026-09-18).
  - `--non-interactive` runs without prompts and is the default when the CLI detects an agent. Exit codes: 0 success, 1 operational failure, 2 usage error ([global options](https://vercel.com/docs/cli/global-options)).
- **Project selection:** `--project`, then `VERCEL_PROJECT_ID`, then `.vercel/project.json`. In CI, set `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` to skip linking ([global options](https://vercel.com/docs/cli/global-options)). Linking writes `.vercel/project.json` ([project linking](https://vercel.com/docs/cli/project-linking), updated 2026-08-11).
- **Auth:** `--token` or `VERCEL_TOKEN`; the variable is recommended because arguments can show up in process lists and logs ([global options](https://vercel.com/docs/cli/global-options)).

**What needs a human** (Documented)

- `vercel login` uses the OAuth 2.0 Device Flow: a person approves the sign-in in a browser. Email login and the `--github`, `--gitlab`, `--bitbucket` and `--oob` flags stopped being supported on 2026-02-26 ([changelog](https://vercel.com/changelog/new-vercel-cli-login-flow)).
- Or a person creates a token on the Account Tokens page, choosing its scope and expiry. It is shown only once. Creating one through the CLI or API itself requires a full-account token, so the first token always involves a person ([token guide](https://vercel.com/kb/guide/how-do-i-use-a-vercel-api-access-token)).
- `vercel deploy --temporary` needs no login, but it is not available in CI or in an already linked directory, and it expires unless claimed ([vercel deploy](https://vercel.com/docs/cli/deploy)). It suits a trial, not this deployment.

**Live check:** one KB page says tokens expire after 10 days unused ([why the CLI asks for login](https://vercel.com/kb/guide/why-is-vercel-cli-asking-me-to-log-in)), while the token guide describes an expiry you choose. Treat a chosen expiry as the rule only after seeing what the token page offers.

### Hobby limits and terms that matter (Documented)

| Item | Hobby |
|---|---|
| Use | Non-commercial personal use only |
| Deployments per day | 100 |
| CLI source upload | 100 MB, 15,000 files |
| Fast Data Transfer / Fast Origin Transfer | 100 GB / 10 GB per month |
| CDN requests | 1,000,000 per month |
| Over the limit | Usually wait 30 days to use the feature again |
| Password Protection | Not available |

Sources: [Hobby plan](https://vercel.com/docs/plans/hobby) (updated 2026-09-14), [limits](https://vercel.com/docs/limits) (updated 2026-09-16), [deployment protection](https://vercel.com/docs/deployment-protection) (updated 2026-09-15).

- **Commercial use** is any deployment for the financial gain of anyone involved in any part of production, "including a paid employee or consultant writing the code" ([fair use](https://vercel.com/docs/limits/fair-use-guidelines), updated 2026-09-14). **If this project is paid work or done for an employer, Hobby may not be allowed.** Vercel says to contact support when unsure. The owner must decide this.
- **Deployment protection:** Standard Protection covers everything except production domains ([deployment protection](https://vercel.com/docs/deployment-protection)). Preview and per-deployment URLs may therefore ask for a Vercel login, so share the production domain. **Live check:** which scope a new Hobby project gets by default.

## 2. The rewrite that makes `/runs/:id` survive a reload

**Documented.** Put this in `web/vercel.json`, at the project root ([Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite)):

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

The filesystem takes precedence over rewrites, so real files under `/assets` are still served ([vercel.json](https://vercel.com/docs/project-configuration/vercel-json), updated 2026-08-14). If `cleanUrls` is on, leave the extension off the destination ([Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite)).

**Live check:** the pages I read do not state how several `rewrites` entries are ordered. If `/api/:path*` is ever added, put it before the catch-all and confirm that `/api/...` reaches the backend rather than `index.html`.

## 3. Can an external rewrite carry a long-lived SSE stream?

**Documented**

- External rewrites make Vercel a reverse proxy: `/api/:path*` to `https://host/:path*` ([rewrites](https://vercel.com/docs/routing/rewrites), updated 2026-08-11).
- The proxied request timeout is **120 seconds on every plan**. If the external server does not reply in that time, the result is `ROUTER_EXTERNAL_TARGET_ERROR` ([limits](https://vercel.com/docs/limits)).
- That limit is not a cap on total duration. The backend can run longer if it "continues sending data at least once every 120 seconds" ([changelog, 2025-05-08](https://vercel.com/changelog/cdn-origin-timeout-increased-to-two-minutes)). The limits page alone reads more strictly, so this rests on a changelog entry.
- Projects created on or after 2026-04-06 honour upstream cache headers on rewrites by default. Setting `x-vercel-enable-rewrite-caching: 0` turns that off ([rewrites](https://vercel.com/docs/routing/rewrites)). Responses with `no-cache` are not cacheable ([CDN cache](https://vercel.com/docs/caching/cdn-cache), updated 2026-09-14).
- The backend side is ready: FastAPI's `EventSourceResponse` pings every 15 seconds when idle and sets `Cache-Control: no-cache` and `X-Accel-Buffering: no` ([FastAPI SSE](https://fastapi.tiangolo.com/tutorial/server-sent-events/)). `clients/web.py` uses it. The 15-second ping is what the HTML standard suggests for proxies that drop idle connections ([WHATWG SSE](https://html.spec.whatwg.org/multipage/server-sent-events.html)).

**Inference:** the pings should keep the stream inside the 120-second gap, so a rewrite probably works.

**Live check (no Vercel page I found answers these)**

- Whether the proxy buffers `text/event-stream`. No Vercel doc I read mentions SSE through a rewrite, and the [reverse proxy guide](https://vercel.com/kb/guide/vercel-reverse-proxy-rewrites-external) covers no timeouts or streaming. A search of vercel.com found only community threads, which I did not rely on.
- Whether a hard cap on total duration exists. Test a stream open for more than 10 minutes, with events arriving as they are sent.
- Whether proxied bytes count against the 10 GB Fast Origin Transfer allowance. The pages I read do not say.
- Whether the first byte arrives within 120 seconds when the backend host is waking from sleep. A slower wake would surface as `ROUTER_EXTERNAL_TARGET_ERROR`, which is an error status, and that matters below.

### Rewrite compared with direct

| | Rewrite through Vercel | Browser calls the host directly |
|---|---|---|
| Same-origin paths | Yes: `client.ts`, `stream.ts` and download links stay as they are | No: needs a base URL at build time |
| CORS | Not needed | Needed on the backend |
| `<a download>` | Honoured (same origin) | Attribute ignored, relies on `Content-Disposition` |
| Stream limits | 120-second gap, buffering unknown | None from Vercel |
| Backend guards | Sees Vercel's forwarded host and IP headers | Sees the Vercel page's `Origin`, which `same_origin` refuses today |
| Secret to the backend | Vercel can attach a header the browser never sees ([rewrites](https://vercel.com/docs/routing/rewrites)) | Anything sent is visible in the browser |

**Reconnect risk either way:** an event stream reconnects after a network error, but a non-200 response or a wrong content type fails it for good ([WHATWG SSE](https://html.spec.whatwg.org/multipage/server-sent-events.html)). So a 5xx while the backend wakes stops `EventSource` permanently, and the UI must open a new one. Also, `events()` in `web.py` sets no event `id`, so the browser sends no `Last-Event-ID`. A reconnect gets the replay from the start of the buffer.

## 4. `EventSource`, `fetch` and `<a download>` across origins

### `EventSource` (Documented)

- The only option is `withCredentials`, so custom headers cannot be set ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/EventSource/EventSource)). A token would have to go in the query string or a cookie. **This matters for ticket 03:** a custom auth header cannot protect the stream without replacing `EventSource` with a `fetch`-based reader.
- It uses CORS. Credentials mode is `include` only when `withCredentials` is true, and the cache mode is `no-store` ([WHATWG SSE](https://html.spec.whatwg.org/multipage/server-sent-events.html)).
- Because it is a GET with only a safelisted `Accept` header, it sends no preflight (**Inference** from the Fetch rules below). The response needs `Access-Control-Allow-Origin`.

### `fetch` and preflight (Documented)

- A preflight is sent for a non-safelisted method, or for any CORS-unsafe request header. Every header outside the safelist is unsafe, so **a custom header forces a preflight** ([Fetch §4.4 and §2.2.2](https://fetch.spec.whatwg.org/)).
- Safelisted: `Accept`, `Accept-Language`, `Content-Language`, `Range` (a simple single range), and `Content-Type` only for `application/x-www-form-urlencoded`, `multipart/form-data` or `text/plain` ([MDN CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS)). **So a POST with `Content-Type: application/json` is preflighted**, as are PUT, PATCH and DELETE.
- The preflight is an `OPTIONS` request with no credentials. The backend must answer with `Access-Control-Allow-Methods` and `Access-Control-Allow-Headers`. `Access-Control-Max-Age` caches the answer: the default is 5 seconds and browsers apply their own ceiling ([MDN CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS), [Fetch](https://fetch.spec.whatwg.org/)).
- `*` is honoured in `Access-Control-Allow-Headers` only without credentials, and it never covers `Authorization`, which must be named ([Fetch §4.8](https://fetch.spec.whatwg.org/)).
- With credentials, `Access-Control-Allow-Origin` must be the exact origin, with `Access-Control-Allow-Credentials: true`. An echoed origin should also send `Vary: Origin` ([MDN CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS)).
- Response headers beyond the safelisted set are hidden from JavaScript unless named in `Access-Control-Expose-Headers` ([MDN CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS)).

### `<a download>` (Documented)

- `download` works only for same-origin URLs, same-origin `blob:` and `data:`. On other URLs "the `download` attribute is ignored" and a normal navigation happens, though `Content-Disposition` can still cause a download ([MDN `<a>`](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/a)). The HTML standard frames this as: across origins, the attribute must be combined with `Content-Disposition: attachment` ([WHATWG links](https://html.spec.whatwg.org/multipage/links.html)).
- `Content-Disposition: attachment; filename="..."` makes the browser download and supplies the name, and that filename overrides the attribute's value ([MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Disposition)).
- **This repo:** `web.py` line 204 returns `FileResponse(path, filename=...)`. The installed Starlette defaults to `content_disposition_type="attachment"` and sets the header (`starlette/responses.py`, lines 314 and 331). So `BriefView.tsx`'s links should still download across origins, with no backend change (**Inference**; confirm with one click on the deployed site).
- A plain link sends no custom headers, so a header-based auth scheme would break these links. They would have to become `fetch` plus a `blob:` URL (**Inference**).

## 5. `VITE_*` variables on Vercel

**Documented**

- Vite statically replaces `VITE_*` at build time and exposes them in client code, so they must not hold secrets. Variables already in the process environment beat `.env` files ([Vite env](https://vite.dev/guide/env-and-mode)).
- Vercel exposes project variables during the Build Step, and changes apply only to new deployments ([environment variables](https://vercel.com/docs/environment-variables), updated 2026-09-17). **Inference:** changing the value needs a rebuild, and redeploying must not reuse an old build output.
- Setting one with the CLI, stored as Config, with no prompts ([vercel env](https://vercel.com/docs/cli/env), updated 2026-08-20):

  ```bash
  vercel env add VITE_API_URL production --value "https://host" --no-sensitive --yes
  ```

  Production and Preview default to Secret, so pass `--no-sensitive` for a value that ships to browsers anyway. `vercel env update` changes an existing one. Piping through stdin also works.
- One deployment only: `vercel --build-env VITE_API_URL=https://host`. **Do not use `--env`:** it provides variables at runtime, which a static bundle never reads ([vercel deploy](https://vercel.com/docs/cli/deploy)).
- `vercel build` with `--prebuilt` uses values from `vercel pull`, and values already in build output cannot be changed at upload ([vercel deploy](https://vercel.com/docs/cli/deploy)).

**Live check:** after deploying, grep the built JS for the host to confirm the value was baked in.

## Live checks, in one place

1. SSE through a rewrite: buffering, and a stream held open past 10 minutes. Only needed if tickets 03 and 05 choose the rewrite.
2. Rewrite order with `/api/:path*` before the catch-all. Same condition.
3. Whether proxied traffic counts against Fast Origin Transfer. Same condition.
4. Default deployment protection scope on a new Hobby project.
5. Token expiry options on the Account Tokens page.
6. A cross-origin Brief download with one click on the deployed site.
7. `VITE_API_URL` present in the built bundle.
