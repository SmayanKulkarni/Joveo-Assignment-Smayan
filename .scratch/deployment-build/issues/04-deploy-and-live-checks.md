# Deploy and live checks

Status: open
Blocked by: [Frontend base URL and access code prompt](02-frontend-base-url-and-code-prompt.md), [Container and Blueprint](03-container-and-space-files.md), the manual list in [Cut build tickets and the manual list](../../deployment/issues/06-cut-build-tickets-and-the-manual-list.md)

Render deploys from GitHub, so what is pushed is what runs.

1. Commit the working tree and push to `master`, with the user's approval.
2. The user creates the Blueprint. The Render URL is now known.
3. Set `VITE_API_URL` on Vercel and deploy `web/` with `--prod`.
4. The user sets `WEB_ORIGIN` on Render to the Vercel production URL and adds the monitor.

Live checks on the deployed pair, using `LANGSMITH_TRACING` as set and one full real Run: tokens stream as they arrive and survive a quiet minute; `/runs/:id` survives a reload; a Pause can be answered; a wrong code is refused; a Brief downloads; and the service doesn't run out of memory, which Render's events would show.

If the stream arrives in bursts, add `X-Accel-Buffering: no` and `Cache-Control: no-cache` to the events response. If memory runs out, lower `LLM_CONCURRENCY` and `JEV_CONCURRENCY`.
