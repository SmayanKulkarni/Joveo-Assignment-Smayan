# Cut build tickets and the manual list

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by: [What survives a restart](04-what-survives-a-restart.md), [Point the frontend at the backend](05-point-the-frontend-at-the-backend.md)

## Question

What are the ordered build slices, including the Dockerfile and how the backend is deployed, and what exactly must the user do by hand?

## Answer

Build slices, in order, are in [`.scratch/deployment-build/issues/`](../../deployment-build/issues/).

Only the user can do these. The first three can happen now; the rest wait until the code is pushed.

1. **OpenRouter key.** Create a new key with a credit limit you can afford to lose, and keep it ready for step 5.
2. **Accounts.** Sign up for Render with GitHub, allowing it access to this repo, and for UptimeRobot.
3. **Vercel.** Run `npx vercel login`. Hobby is non-commercial only, so check that this assessment counts as personal work.
4. **Choose an access code.** Any long phrase.
5. **Create the backend.** In Render, choose New, then Blueprint, pick the repo, and paste the values it asks for: the new OpenRouter key, your access code, and the rest from `.env`. Leave `WEB_ORIGIN` until the agent gives you the Vercel URL, then add it.
6. **Monitor.** In UptimeRobot, add an HTTP monitor on `https://<render-host>/api/meta` every 5 minutes.
7. **Final check.** Open the Vercel URL before sharing it.

The agent does the rest: the code, the commit and push once you approve them, the Vercel deploy, and the live checks.
