# Deployment

Label: wayfinder:map
Parent: [Talent Market Scout: HLD](../talent-scout-hld/map.md) (the hosting that [Web UI](../web-ui/map.md) ruled out of scope)

## Destination

Build tickets in `.scratch/deployment-build/issues/` and a short list of what only the user can do, precise enough to go straight from this repo to a public URL: backend on a Hugging Face Docker Space, frontend on Vercel. Nothing is left to decide. Doing the deployment is the next effort.

## Notes

- Domain: hosting the existing FastAPI app and `web/` SPA. Vocabulary: `GLOSSARY.md`. Upstream: [docs/lld/web-ui.md](../../docs/lld/web-ui.md). Deadline Mon 2 Nov 2026, 9:00 AM, so the simplest thing that works wins.
- Skills: `research` for research tickets. Nothing here touches LangChain.
- On 2026-11-01 the user told the agent to make every decision and report only what needs manual input. Each ticket says the agent decided it.
- Decided at charting:
  - **One backend process.** The Controller stays in-process, one worker, as the Web UI map decided. No queue, workers or database service.
  - **A single shared deployment.** No user accounts: everyone with the URL sees the same Run history.
  - **CLIs do the deploying.** `hf` (through `uvx`) and `vercel` (through `npx`) work without a global install. The Hugging Face and Vercel MCP connectors are optional, for reading docs, logs and deployment state.

## Decisions so far

<!-- one line per closed ticket -->

## Not yet specified

Nothing beyond the open tickets.

## Out of scope

- Accounts, per-user history, roles, a queue or workers: the Infra shell, [future scope](../../docs/lld/future-scope.md).
- A custom domain, CI/CD and staging: a manual deploy meets the deadline.
- Backups of Run history.
- Doing the deployment: the next effort, from the build tickets.
