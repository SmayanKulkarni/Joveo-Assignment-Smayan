# Point the frontend at the backend

Type: grilling
Status: open
Assignee:
Blocked by: [Research: serving the SPA from Vercel and reaching the backend](02-research-vercel-spa-and-cross-origin-sse.md), [Open the backend to the internet](03-open-the-backend-to-the-internet.md)

## Question

Every call uses a relative `/api` path: `client.ts`, `stream.ts`, and the Brief download links in `BriefView.tsx`. Does the browser reach the Space through a Vercel rewrite or directly? What is the smallest frontend change, and how does the UI handle a Space that is waking up?
