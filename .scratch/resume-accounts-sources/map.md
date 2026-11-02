# Resumes, accounts and more job sources

Label: wayfinder:map
Parent: [Talent Market Scout: HLD](../talent-scout-hld/map.md) (the Infra shell's multi-user phase and the Long-term memory pass that [future scope](../../docs/lld/future-scope.md) deferred, plus new jobs sources)

## Destination

An LLD, `docs/lld/accounts-resume-sources.md`, plus updates to the Gateway, Collection, Runtime and Web UI LLDs where they change, and build tickets in value order in `.scratch/resume-accounts-sources-build/issues/`. Together they must be precise enough to build these four things straight from the docs:

1. A resume agent that reads an uploaded resume and finds Postings that match it.
2. Sign-up and login, Runs that belong to a user, and a User Profile learned from that user's earlier Runs that improves their later Runs.
3. Arbeitnow as a new jobs source and Collection tool.
4. Whichever of JSearch, Active Jobs DB, LinkedIn Job Search API, Indeed Scraper API and Glassdoor Real-Time earn a place, with the gateway and tools reshaped to hold many sources.
5. Guardrails on every LLM node, old and new, built from open-source frameworks and open-weight models: for each node, what it checks, where the check lives, and what a Run does when it trips.

When the map is done, nothing is left to decide. Writing the code is the next effort.

## Notes

- Domain: the existing Talent Market Scout. Vocabulary is in `GLOSSARY.md`. Fixed upstream: [docs/HLD.md](../../docs/HLD.md), [Gateway LLD](../../docs/lld/gateway.md), [Collection LLD](../../docs/lld/collection.md), [Runtime LLD](../../docs/lld/runtime.md), [Web UI LLD](../../docs/lld/web-ui.md), [future scope](../../docs/lld/future-scope.md), and [Deployment](../deployment/map.md) (Render free web service plus Vercel; nothing on disk survives a restart).
- Skills: `grilling` and `domain-modeling` for grilling tickets, `prototype` for prototype tickets, `research` for research tickets. Load `langchain-router` first for any ticket that touches graph nodes, tools, the Store, the checkpointer or guardrail middleware.
- Standing preferences: Pydantic v2, `uv`, Python 3.12, `src/talent_scout/`, `pytest`, npm with exact pins in `web/`. Keep the solution as small as possible: no abstraction until a second user needs it. Code comments are short and say why.
- Charting decisions, and the reason behind each, are in [decisions.md](decisions.md). That file is their one home, so this map doesn't repeat them.
- [LLM nodes](assets/llm-nodes.md) lists every LLM call today, the text it reads and the guards it already has. The guardrail tickets start from it.
- On 2026-11-02 the user told the agent to chart this map alone, and later the same day to chart the guardrails part alone too. That covers charting only. Grilling and prototype tickets stay HITL unless the user says otherwise.

## Decisions so far

<!-- one line per closed ticket -->

- [Research: Arbeitnow job board API](issues/01-research-arbeitnow.md): keyless, but every filter runs locally on an hourly snapshot of the whole feed (about 21 pages); only DE, GB, FR, CH and NL, about 7 days deep, with no salary, category or close date; a link back is required, and the non-commercial clause needs asking about.
- [Research: JSearch on RapidAPI](issues/02-research-jsearch.md): Google for Jobs data with Advertised salary, so heavy Duplicates against Adzuna; one call with `num_pages` instead of paging, about 8.5 s per call, quota headers feed `calls_left`; the free plan is 200 credits a month (about three Runs).
- [Research: durable storage for accounts and Runs](issues/06-research-durable-storage-for-accounts-and-runs.md): Neon Free Postgres in Oregon (Render's free Postgres expires after 30 days, and Supabase and Turso pause), `langgraph-checkpoint-postgres` 3.2.0 fits the pins, prune finished Runs to stay within 1 GB, the gateway cache stays on local SQLite, and resumes are stored as text.
- [Research: signing in across Vercel and Render](issues/07-research-signing-in-across-vercel-and-render.md): proxy `/api` through a Vercel rewrite so a `__Host-` `SameSite=Lax` cookie works everywhere and `EventSource` needs no CORS (streaming through the rewrite still needs a preview test); the fallback is a `Partitioned` cookie, which works in Chrome, Firefox and Safari 26.2+; no tokens in the SSE URL; keep the `Origin` check; `pwdlib[argon2]` for passwords.
- [Research: Fantastic Jobs APIs](issues/03-research-fantastic-jobs-apis.md): both RapidAPI listings and the direct portal sell one v1 API (`/active-ats` for career sites, `/active-jb` for LinkedIn); quota counts every job returned (a 600-Posting Run costs about 600 credits); RapidAPI's free plans renew monthly (250 jobs); salary is Advertised and `id` is stable; take the career-site feed and leave out LinkedIn, whose agreement forbids reusing its data.
- [Research: Indeed Scraper API](issues/04-research-indeed-scraper-api.md): a POST that waits or returns a task id to poll, so it needs a non-retried POST and a timeout of about 60 s; salary is Advertised; the free plan is 25 calls a month; the terms risk is high, because Indeed's rules ban scrapers and the listing has no terms of its own.
- [Research: Glassdoor Real-Time](issues/05-research-glassdoor-real-time.md): an unofficial API with no terms and undocumented fields; not a postings source, only a candidate salary benchmark; its pay is employee-reported and modelled, a third kind that is neither Advertised nor Estimated; the free plan gives about 50 salary lookups a month.
- [Research: reading resume files](issues/08-research-reading-resume-files.md): pypdf in layout mode for PDFs (the only library that kept two columns in order) and the standard library for DOCX; scanned PDFs are refused; the upload is a raw body capped at 2 MB with no `python-multipart` and nothing written to disk; one cheap structured call with no name or contact fields, and the skill grounding check is reused; parse outside the graph, redact contact details, and disable tracing and caching so resumes never reach LangSmith or SQLite.

## Not yet specified

- **Does the profile actually help?** How to tell that a User Profile improves results: a before-and-after on seeded Runs, a thumbs-up on Postings, or nothing measured. This becomes specifiable once [What a User Profile holds](issues/16-what-a-user-profile-holds.md) and [How a User Profile shapes a Run](issues/19-how-a-user-profile-shapes-a-run.md) settle what changes.
- **Personal data.** Retention, deletion and export of resumes and profiles, and what parts of a resume may reach OpenRouter and LangSmith traces. This depends on what [Reading resume files](issues/08-research-reading-resume-files.md) finds and on where [Accounts and sign-in](issues/14-accounts-and-sign-in.md) stores things.
- **Deployment changes.** New env vars and API keys, a database service if [Durable storage](issues/06-research-durable-storage-for-accounts-and-runs.md) picks one, guard models or their memory on Render if [Guardrails for the existing LLM nodes](issues/24-guardrails-for-the-existing-llm-nodes.md) runs any locally, and `render.yaml` and Vercel changes. These can be written once storage, sources and guards are chosen.
- **Watching the guardrails.** Whether trip counts and false positives are tracked over time (a Run Notes count, a LangSmith tag, or nothing), and how a rail's threshold gets tuned once real Runs show what it catches. This becomes specifiable once [Guardrails for the existing LLM nodes](issues/24-guardrails-for-the-existing-llm-nodes.md) picks the rails.
- **Glossary.** New terms such as Resume, User Profile, Match and Salary Benchmark get written as each ticket fixes them. The last ticket checks that `GLOSSARY.md` agrees with the LLDs.

## Out of scope

- Writing the code. That is the build effort after this map.
- OAuth or social login, email verification, password reset by email, and two-factor auth. Basic auth means email and password.
- Roles beyond "a user owns their own Runs": admins, teams, organisations and sharing Runs.
- Applying to jobs, writing cover letters, or rewriting the resume for the user.
- Scraping job sites ourselves. Only APIs.
- Billing, or paid plans for users.
- Hosted vendor guardrails: AWS Bedrock Guardrails, Azure AI Content Safety, Lakera and the like. The user asked for open-source frameworks. Open-weight guard models served by OpenRouter are still in.
