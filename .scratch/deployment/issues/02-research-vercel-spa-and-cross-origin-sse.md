# Research: serving the SPA from Vercel and reaching the backend

Type: research
Status: open
Assignee:
Blocked by: none

## Question

What do Vercel's and the browser standards' primary docs say about serving this Vite SPA and reaching an API on another host?

- Deploying a Vite app from a `web/` subdirectory with the `vercel` CLI, non-interactive use, and what login needs a human. Hobby plan limits and terms that matter here.
- The `vercel.json` rewrite that makes `/runs/:id` survive a reload.
- Can a Vercel external rewrite (`/api/*` to another host) carry a long-lived SSE stream? Is there a proxy timeout or buffering? Compare with the browser calling the other host directly.
- `EventSource` and `fetch` across origins: the CORS headers needed, and whether a custom header forces a preflight. `<a download>` across origins: is the attribute ignored, and what does `Content-Disposition` do?
- How `VITE_*` variables get baked in at build time on Vercel, and how the CLI sets them.
