# Decisions: Resumes, accounts and more job sources

The agent made these decisions alone while charting [the map](map.md) on 2026-11-02, because the user asked it to. Each one fixes scope or shape before any ticket is worked. Decisions made later, inside tickets, live in their own ticket and get a one-line pointer in the map's Decisions so far. They are not copied here.

## Process

- **Branch `resume-accounts-and-sources`**, cut from `master` at `9ed60ac`. The map and its tickets are committed there.
- **Local-markdown tracker**, the same as every earlier map: `map.md`, `issues/NN-name.md` with `Type`, `Status`, `Assignee` and `Blocked by` headers, and assets in `assets/`. Blocking is the `Blocked by` line. The frontier is the open tickets with no open blockers and `Assignee: none`.
- **No live grilling at charting.** The user asked for the map to be charted alone, so the breadth-first pass was done against the code and the existing LLDs instead of a conversation. Grilling and prototype tickets are still HITL when they are worked.
- **Research findings go in each ticket's Answer section, with long notes in `assets/`.** This follows the repo's earlier research tickets. It replaces the skill's throwaway `research/<name>` branches, and nothing is pushed, because pushing is outward-facing and the user didn't ask for it.

## Destination

- **Docs and build tickets, not code.** The output is the same as the Web UI and Deployment maps: LLDs precise enough to build from, and build tickets in value order. The code is the next effort.
- **One new LLD, `docs/lld/accounts-resume-sources.md`, covering accounts, profiles and resumes.** New sources go into the existing Gateway and Collection LLDs, because those already own sources and tools. Three separate new LLDs would split one user story (sign in, upload a resume, get better Runs) across files.
- **All four asks are in one map**, because they share decisions. The resume agent calls the same search tools that the new sources add. The profile is per user, so it needs accounts. A resume can feed the profile.

## Scope

- **"User level" means data scoped per user**: every Run, resume and profile belongs to exactly one user, and a user sees only their own. Roles and admins are out of scope. If the user meant roles, the destination needs redrawing.
- **Basic auth means email and password only.** Password reset and email verification would need an email provider, so they are out of scope. OAuth too.
- **One kind of account.** The same signed-in user can research a market for a client (the existing Market Brief flow) or find jobs that match their own resume. There is no separate "recruiter" or "candidate" account type.
- **The existing access code is up for replacement, not assumed kept.** [Accounts and sign-in](issues/14-accounts-and-sign-in.md) decides whether accounts replace it or sit beside it.
- **Every API the user listed gets researched, but none is assumed in.** Arbeitnow is in because the user asked for it outright. The RapidAPI and Fantastic Jobs APIs join only if [Which job sources join the gateway](issues/10-which-job-sources-join-the-gateway.md) finds they're worth the quota, latency and terms. Glassdoor Real-Time is a salary API, not a postings API, so it raises its own question: [Salary benchmarks in the Brief](issues/13-salary-benchmarks-in-the-brief.md).
- **The honesty rules carry over.** Stats are computed by code, Advertised and Estimated pay are never pooled, and every Assumption goes in the Run Notes. A profile or resume that changes a Run must show up in the Run Notes the same way an Assumption does.

## Shape of the map

- **Research first, in parallel.** There are eight research tickets: one per vendor family (Arbeitnow, JSearch, Fantastic Jobs, Indeed Scraper, Glassdoor), one for durable storage, one for cross-site sign-in, and one for reading resume files. They are AFK and unblocked, so they run in parallel at charting.
- **Durable storage is its own research ticket**, because Deployment decided that nothing on Render's free disk survives a restart. Accounts and profiles that vanish on a redeploy would make item 2 pointless.
- **Cross-site sign-in is its own research ticket**, because the SPA (Vercel) and API (Render) are on different sites, `EventSource` can't send an auth header, and browsers are restricting third-party cookies.
- **A HITL task for API keys.** Judging data quality and real quotas needs live calls, and RapidAPI keys need a human to sign up and subscribe. Research can go ahead from the docs alone. The source decision waits for the keys.
- **Resume purpose is on the frontier.** Whether a resume starts a new kind of Run (ranked Matches) or only seeds a Hiring Request is the biggest fork in item 1, and it needs no research. So it can be grilled while research runs.
- **The last ticket writes the LLDs and cuts build tickets**, the same pattern as the Web UI and Deployment maps.
