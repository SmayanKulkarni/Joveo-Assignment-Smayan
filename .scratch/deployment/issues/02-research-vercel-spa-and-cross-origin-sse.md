# Research: serving the SPA from Vercel and reaching the backend

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

What do Vercel's and the browser standards' primary docs say about serving this Vite SPA and reaching an API on another host?

- Deploying a Vite app from a `web/` subdirectory with the `vercel` CLI, non-interactive use, and what login needs a human. Hobby plan limits and terms that matter here.
- The `vercel.json` rewrite that makes `/runs/:id` survive a reload.
- Can a Vercel external rewrite (`/api/*` to another host) carry a long-lived SSE stream? Is there a proxy timeout or buffering? Compare with the browser calling the other host directly.
- `EventSource` and `fetch` across origins: the CORS headers needed, and whether a custom header forces a preflight. `<a download>` across origins: is the attribute ignored, and what does `Content-Disposition` do?
- How `VITE_*` variables get baked in at build time on Vercel, and how the CLI sets them.

## Answer

Full findings, with sources: [research-vercel-spa-and-cross-origin-sse.md](assets/research-vercel-spa-and-cross-origin-sse.md).

- **Deploying.** `vercel --cwd web --yes --prod` after a human approves the login. Hobby is non-commercial only.
- **Reloads.** Rewrite `/(.*)` to `/index.html`; real files win.
- **Rewrites and SSE.** A 120-second limit is documented, and buffering and total duration are not. Calling the Space directly avoids all of it, but needs CORS and a base URL.
- **CORS.** `EventSource` sends no custom headers and no preflight. JSON and custom headers on `fetch` do force a preflight. A non-200 response ends an `EventSource` for good.
- **Downloads.** `download` is ignored across origins, but the `Content-Disposition: attachment` that `FileResponse` sends still downloads.
- **`VITE_*`.** Baked in at build time, set with `vercel env add`; a change needs a new deployment.
