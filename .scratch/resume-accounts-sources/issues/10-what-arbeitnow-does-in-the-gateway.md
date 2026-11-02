# What Arbeitnow does in the gateway

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [Research: Arbeitnow job board API](01-research-arbeitnow.md)

## Question

Arbeitnow joins as a `Source` beside Adzuna and USAJOBS. What is it for, and with what limits?

- Which countries and which kinds of role it serves. It only covers DE, GB, FR, CH and NL, about 7 days deep, with no salary, category or close date.
- Duplicates against Adzuna in the countries both cover, and whether that changes when Arbeitnow is offered.
- Its budget guard: it's keyless and filters run locally on an hourly snapshot of the whole feed, so the guard may be on snapshot refreshes, not calls. Whether the snapshot is cached in L1 and L2, and what happens to a Run when it's down.
- The non-commercial clause in its terms: ask Arbeitnow, or decide the project's use fits.
- The link back it needs on screen and in `brief.md` (see `ATTRIBUTION` in `gateway/types.py`).

## Answer

Grilled with the user on 2026-11-02. The user accepted every recommendation.

**Item 5 stands:** [Research: job source terms for CSM use](27-research-job-source-terms-for-csm-use.md) questioned it, and the user confirmed on 2026-11-02 that this is a personal project, so nothing changes.

**Amended by [Choosing among the search tools](12-choosing-among-many-search-tools.md):** item 1's five-country limit no longer holds. `search_arbeitnow` is offered on every accepted country, and outside the five it returns remote jobs only. It is still never offered alone.

1. **Where it's offered.** `search_arbeitnow` is offered beside `search_adzuna` only when the plan's country is `de`, `gb`, `fr`, `ch` or `nl`, and never alone. Both Market Brief Runs and the resume agent get it. Its tool description says it is tech-heavy, lists no pay and holds only about the last 7 days. The model picks per role from that, with no role filter in code.
2. **No pay.** Arbeitnow Postings count toward demand and skills, and pay stats use only the Postings that have pay, as today. A closing Caveat, "Mostly no pay: N of M Postings are from Arbeitnow, which lists no salary", is logged when more than half the Sample comes from Arbeitnow. It mirrors "Mostly federal".
3. **Duplicates with Adzuna.** A missing salary never blocks a merge, because unknown pay doesn't contradict known pay, and the Posting that has pay wins. Today `_same_pay` (`gateway/coalesce.py`) refuses that merge, so it has to change. Cross-source merging already happens in Collection (`collection/nodes.py`). The exact ranking is left to [One gateway for many sources](11-one-gateway-for-many-sources.md).
4. **Budget guard and outages.** No daily call counter. The guard is at most one full walk of the feed an hour, done lazily the first time a Run needs it. A failure or 429 partway through a walk is `SourceUnavailable`: the half-walked snapshot is thrown away, and the Run goes on with Adzuna and the usual failure Caveat. Where the snapshot is cached is left to ticket 11.
5. **Non-commercial clause.** We decide the project's use fits: it is free, non-commercial and shows no ads, and the Brief shows stats and links, not republished descriptions, which keeps clear of the anti-mirroring clause. The LLD records this reasoning. A courtesy email goes to contact@arbeitnow.com, and nothing waits on its reply.
6. **Link back.** `ATTRIBUTION` gains an Arbeitnow entry linking to arbeitnow.com. Run Notes `attribution` becomes one line naming every source in the Sample that needs credit, for example "Jobs data provided by The Adzuna API and Arbeitnow", shown in `brief.md`, the Brief footer and the resume Match screen. Each Arbeitnow Posting's URL already points at an arbeitnow.com page, and that stays.
