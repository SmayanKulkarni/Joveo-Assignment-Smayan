# Choose a free backend host

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: [Research: running the backend on a Hugging Face Docker Space](01-research-hf-docker-spaces.md)

## Question

The user requires free hosting, and a Docker Space needs PRO. Which free host can run one long-lived FastAPI process with SSE from a Dockerfile?

## Answer

**Render's free web service.** Decided by the agent.

Documented by [Render](https://render.com/docs/free):

- 750 free instance hours a month, enough to stay up for a whole month (744 hours at most).
- Spins down after 15 minutes with no inbound traffic, and takes about a minute to spin back up.
- The filesystem is ephemeral: changes are lost on redeploy, restart or spin-down. Render may restart a free service at any time.
- Render may suspend a free service for running out of hours or bandwidth, or for unusually high traffic it starts itself.
- A [Blueprint](https://render.com/docs/blueprint-spec) takes `runtime: docker` with `plan: free`, and `sync: false` prompts for secrets at creation.
- The app [binds to `0.0.0.0` on `PORT`](https://render.com/docs/web-services), default 10000. [`RENDER_EXTERNAL_HOSTNAME`](https://render.com/docs/environment-variables) holds its host.

Rejected:

- **Hugging Face:** a Docker Space needs [PRO](https://huggingface.co/docs/hub/spaces-overview).
- **Koyeb:** its [pricing page](https://www.koyeb.com/pricing) lists no free compute, and its lowest compute plan is $29/month.
- **Fly.io:** reported by a third-party comparison to have no free compute for new accounts. Not checked at the source.
- **Northflank:** a free Sandbox is reported, but no current primary source was checked, and the deadline favours the documented option.

Not confirmed at the source:

- RAM and CPU: the pages read didn't state them. Treat memory as the main risk. The backend used 108 MB after import on this machine, and a full Run was not measured.
- Whether a card is needed: the free page implies not, since it describes what happens without a payment method.
- SSE behaviour through Render's proxy, and private repo access. Both get checked at deploy.
