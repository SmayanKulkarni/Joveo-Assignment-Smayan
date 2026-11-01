# Deployment

Label: wayfinder:map
Parent: [Talent Market Scout: HLD](../talent-scout-hld/map.md) (the hosting that [Web UI](../web-ui/map.md) ruled out of scope)

## Destination

Build tickets in `.scratch/deployment-build/issues/` and a short list of what only the user can do, precise enough to go straight from this repo to a public URL: backend on a free Render web service, frontend on Vercel, at no cost. Nothing is left to decide. Doing the deployment is the next effort.

Redrawn 2026-11-01: the user first named Hugging Face, then required a free backend once research showed a Docker Space needs a paid plan.

## Notes

- Domain: hosting the existing FastAPI app and `web/` SPA. Vocabulary: `GLOSSARY.md`. Upstream: [docs/lld/web-ui.md](../../docs/lld/web-ui.md). Deadline Mon 2 Nov 2026, 9:00 AM, so the simplest thing that works wins.
- Skills: `research` for research tickets. Nothing here touches LangChain.
- On 2026-11-01 the user told the agent to make every decision and report only what needs manual input. Each ticket says the agent decided it.
- Decided at charting:
  - **One backend process.** The Controller stays in-process, one worker, as the Web UI map decided. No queue, workers or database service.
  - **A single shared deployment.** No user accounts: everyone with the URL sees the same Run history.
  - **Deploying.** A `render.yaml` Blueprint deploys the backend from GitHub, and `vercel` through `npx` deploys the frontend. MCP connectors are optional, for reading docs, logs and deployment state.

## Decisions so far

<!-- one line per closed ticket -->

- [Research: running the backend on a Hugging Face Docker Space](issues/01-research-hf-docker-spaces.md): a Docker Space needs PRO ($9/month) even on free hardware; the disk is lost on restart; Protected hides the source; SSE through the proxy needs a live check.
- [Research: serving the SPA from Vercel and reaching the backend](issues/02-research-vercel-spa-and-cross-origin-sse.md): CLI deploy after a human login; SSE through a rewrite is undocumented, so a direct call is safer; Hobby is non-commercial only.
- [Open the backend to the internet](issues/03-open-the-backend-to-the-internet.md): a shared access code on POSTs only, a capped OpenRouter key, one allowed CORS origin, and `RENDER_EXTERNAL_HOSTNAME` trusted.
- [What survives a restart](issues/04-what-survives-a-restart.md): nothing is guaranteed; history lives on the ephemeral disk, and a free monitor stops the 15-minute spin-down that would wipe it.
- [Point the frontend at the backend](issues/05-point-the-frontend-at-the-backend.md): direct calls through `VITE_API_URL`, a `window.prompt` for the code, and a retrying wake message.
- [Choose a free backend host](issues/07-choose-a-free-backend-host.md): Render's free web service; Hugging Face needs PRO, Koyeb lists no free compute, and Fly.io is reported to have no free tier.
- [Cut build tickets and the manual list](issues/06-cut-build-tickets-and-the-manual-list.md): four build slices in `.scratch/deployment-build/issues/` and the steps only the user can do. The map is complete.

## Not yet specified

Nothing beyond the open tickets.

## Out of scope

- Accounts, per-user history, roles, a queue or workers: the Infra shell, [future scope](../../docs/lld/future-scope.md).
- A custom domain, CI/CD and staging: a manual deploy meets the deadline.
- Backups of Run history.
- Doing the deployment: the next effort, from the build tickets.
- Hugging Face Spaces: a Docker Space needs a paid plan, and the user requires free hosting.
