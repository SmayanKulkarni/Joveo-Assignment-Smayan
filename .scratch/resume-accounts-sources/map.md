# Resumes, accounts and more job sources

Label: wayfinder:map
Parent: [Talent Market Scout: HLD](../talent-scout-hld/map.md) (the Infra shell's multi-user phase and the Long-term memory pass that [future scope](../../docs/lld/future-scope.md) deferred, plus new jobs sources)

## Destination

An LLD, `docs/lld/accounts-resume-sources.md`, plus updates to the Gateway, Collection, Runtime and Web UI LLDs where they change, and build tickets in value order in `.scratch/resume-accounts-sources-build/issues/`. Together they must be precise enough to build these four things straight from the docs:

1. A resume agent that reads an uploaded resume and finds Postings that match it.
2. Sign-up and login, Runs that belong to a user, and a User Profile learned from that user's earlier Runs that improves their later Runs.
3. Arbeitnow as a new jobs source and Collection tool.
4. Whichever of JSearch, Active Jobs DB, LinkedIn Job Search API, Indeed Scraper API and Glassdoor Real-Time earn a place, with the gateway and tools reshaped to hold many sources.

When the map is done, nothing is left to decide. Writing the code is the next effort.

## Notes

- Domain: the existing Talent Market Scout. Vocabulary is in `GLOSSARY.md`. Fixed upstream: [docs/HLD.md](../../docs/HLD.md), [Gateway LLD](../../docs/lld/gateway.md), [Collection LLD](../../docs/lld/collection.md), [Runtime LLD](../../docs/lld/runtime.md), [Web UI LLD](../../docs/lld/web-ui.md), [future scope](../../docs/lld/future-scope.md), and [Deployment](../deployment/map.md) (Render free web service plus Vercel; nothing on disk survives a restart).
- Skills: `grilling` and `domain-modeling` for grilling tickets, `prototype` for prototype tickets, `research` for research tickets. Load `langchain-router` first for any ticket that touches graph nodes, tools, the Store or the checkpointer.
- Standing preferences: Pydantic v2, `uv`, Python 3.12, `src/talent_scout/`, `pytest`, npm with exact pins in `web/`. Keep the solution as small as possible: no abstraction until a second user needs it. Code comments are short and say why.
- Charting decisions, and the reason behind each, are in [decisions.md](decisions.md). That file is their one home, so this map doesn't repeat them.
- On 2026-11-02 the user told the agent to chart this map alone. That covers charting only. Grilling and prototype tickets stay HITL unless the user says otherwise.

## Decisions so far

<!-- one line per closed ticket -->

## Not yet specified

- **Does the profile actually help?** How to tell that a User Profile improves results: a before-and-after on seeded Runs, a thumbs-up on Postings, or nothing measured. This becomes specifiable once [What a User Profile holds](issues/16-what-a-user-profile-holds.md) and [How a User Profile shapes a Run](issues/19-how-a-user-profile-shapes-a-run.md) settle what changes.
- **Personal data.** Retention, deletion and export of resumes and profiles, and what parts of a resume may reach OpenRouter and LangSmith traces. This depends on what [Reading resume files](issues/08-research-reading-resume-files.md) finds and on where [Accounts and sign-in](issues/14-accounts-and-sign-in.md) stores things.
- **Deployment changes.** New env vars and API keys, a database service if [Durable storage](issues/06-research-durable-storage-for-accounts-and-runs.md) picks one, and `render.yaml` and Vercel changes. These can be written once storage and sources are chosen.
- **Glossary.** New terms such as Resume, User Profile, Match and Salary Benchmark get written as each ticket fixes them. The last ticket checks that `GLOSSARY.md` agrees with the LLDs.

## Out of scope

- Writing the code. That is the build effort after this map.
- OAuth or social login, email verification, password reset by email, and two-factor auth. Basic auth means email and password.
- Roles beyond "a user owns their own Runs": admins, teams, organisations and sharing Runs.
- Applying to jobs, writing cover letters, or rewriting the resume for the user.
- Scraping job sites ourselves. Only APIs.
- Billing, or paid plans for users.
