# What survives a restart

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [Choose a free backend host](07-choose-a-free-backend-host.md)

## Question

`gateway_db`, `runs_db` and `runs_dir` are local files. Given what the host keeps across spin-down and restart, what should hold Run history and the Gateway's quota counter and cache? In particular, does losing `adzuna_daily_limit`'s counter risk the real Adzuna quota?

## Answer

Decided by the agent, as the user asked. Originally decided for Hugging Face, and redone for Render.

- **The files stay on the ephemeral disk**, at their default paths, in a work directory owned by the container user. No code changes. Render's free database expires after 30 days and would mean replacing the SQLite checkpointer the day before the deadline.
- **A free monitor keeps the service awake.** Without one, 15 idle minutes wipes all history and stops any Run left without an open tab. UptimeRobot's free plan checks `/api/meta` every 5 minutes, and 750 free hours cover a full month. This reduces the risk but doesn't remove it, since Render may still restart a free service at any time.
- **An open tab also counts.** The sidebar polls the Run list, and that is inbound traffic.
- **The quota counter.** A restart resets the local count, so the guard can under-count on a day with restarts. Adzuna still enforces the real limit. Accepted.
- **For a reviewer.** Don't push to `master` or change variables after sharing the URL, because a redeploy clears history.
