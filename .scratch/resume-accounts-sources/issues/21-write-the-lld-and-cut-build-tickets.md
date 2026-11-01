# Write the LLD and cut build tickets

Type: task
Status: open
Assignee: none
Blocked by: [One gateway for many sources](11-one-gateway-for-many-sources.md), [Choosing among many search tools](12-choosing-among-many-search-tools.md), [Salary benchmarks in the Brief](13-salary-benchmarks-in-the-brief.md), [Matching Postings to a Resume](18-matching-postings-to-a-resume.md), [How a User Profile shapes a Run](19-how-a-user-profile-shapes-a-run.md), [Resume, profile and sign-in screens](20-resume-profile-and-sign-in-screens.md)

## Question

Write `docs/lld/accounts-resume-sources.md` and update the Gateway, Collection, Runtime, Web UI, HLD and future-scope docs and `GLOSSARY.md` so they all agree with every ticket on this map. Then cut build tickets in value order into `.scratch/resume-accounts-sources-build/issues/`.

- Every decision links back to its ticket, the way earlier LLDs do.
- Build order by value, and each build slice is shippable on its own. A likely order: new sources first (smallest and needs no accounts), then accounts and per-user Runs, then resume Runs, then the profile.
- Each build slice names its tests, following the repo's `pytest` and Vitest patterns.
- Check that no fog is left on the map. Graduate or rule out anything still in Not yet specified before closing this ticket.
