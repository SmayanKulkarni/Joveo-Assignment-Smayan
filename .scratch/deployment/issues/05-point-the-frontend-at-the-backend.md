# Point the frontend at the backend

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [Research: serving the SPA from Vercel and reaching the backend](02-research-vercel-spa-and-cross-origin-sse.md), [Open the backend to the internet](03-open-the-backend-to-the-internet.md)

## Question

Every call uses a relative `/api` path: `client.ts`, `stream.ts`, and the Brief download links in `BriefView.tsx`. Does the browser reach the Space through a Vercel rewrite or directly? What is the smallest frontend change, and how does the UI handle a Space that is waking up?

## Answer

Decided by the agent, as the user asked.

- **Directly.** A rewrite would avoid CORS, but its streaming behaviour is undocumented, and a Run can stream for minutes.
- **One base URL.** Export `API = import.meta.env.VITE_API_URL ?? ""` from `client.ts` and use it at the three call sites. It stays empty locally, so the Vite proxy and same-process serving keep working.
- **Access code through a native prompt.** On a 401 `access_denied`, `call()` asks with `window.prompt`, keeps the answer in `localStorage` in a `try/catch`, and retries once. No new screen. Every POST goes through `call()`, so this is one place.
- **Reloads.** `web/vercel.json` rewrites `/(.*)` to `/index.html`.
- **Waking.** A free Render service can take about a minute to spin up, so if `/api/meta` fails, the app shows one line, "Waking the server, this can take a minute", and retries every 5 seconds for 2 minutes, then asks the reader to reload.
