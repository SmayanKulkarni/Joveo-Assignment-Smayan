# Open the backend to the internet

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [Research: running the backend on a Hugging Face Docker Space](01-research-hf-docker-spaces.md), [Research: serving the SPA from Vercel and reaching the backend](02-research-vercel-spa-and-cross-origin-sse.md)

## Question

`clients/web.py` assumes loopback: `TrustedHostMiddleware` allows only localhost, `same_origin` refuses another origin, and `scout serve` binds 127.0.0.1. There is no auth, and every Run spends the user's OpenRouter and Adzuna quota. What changes so a public host is safe from strangers spending that money, with the least code, and without weakening the local guards?

## Answer

Decided by the agent, as the user asked.

- **A shared access code guards spending, and only spending.** New setting `access_code: str | None`. When set, the three POST routes need a matching `X-Access-Code` header, compared with `secrets.compare_digest`, or they return 401 `access_denied`. The check goes in the dependency those routes already share. GETs stay open, so `EventSource` needs no header and no token lands in a URL. Anyone with the URL can read Runs, which fits one shared deployment.
- **A spend cap sits behind the code.** The Space gets its own OpenRouter key with a credit limit, so a leaked code costs at most that limit.
- **One allowed origin.** New setting `web_origin: str | None`. `same_origin` also accepts it, and `CORSMiddleware` allows only it, with GET and POST and the headers `Content-Type` and `X-Access-Code`. Vercel preview URLs are refused on purpose.
- **Hosts.** Add `RENDER_EXTERNAL_HOSTNAME` to the trusted hosts when it is set. A local run has none, so the local guards don't change.
- **Binding.** `scout serve` gains `--host`, default 127.0.0.1. The container passes `--host 0.0.0.0 --port $PORT`.
- **Skipped.** Accounts, rate limits per user and per-Run limits: the credit limit is the ceiling.
