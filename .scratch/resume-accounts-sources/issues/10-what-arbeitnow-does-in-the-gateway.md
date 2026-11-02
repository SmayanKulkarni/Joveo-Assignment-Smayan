# What Arbeitnow does in the gateway

Type: grilling
Status: open
Assignee: none
Blocked by: [Research: Arbeitnow job board API](01-research-arbeitnow.md)

## Question

Arbeitnow joins as a `Source` beside Adzuna and USAJOBS. What is it for, and with what limits?

- Which countries and which kinds of role it serves. It only covers DE, GB, FR, CH and NL, about 7 days deep, with no salary, category or close date.
- Duplicates against Adzuna in the countries both cover, and whether that changes when Arbeitnow is offered.
- Its budget guard: it's keyless and filters run locally on an hourly snapshot of the whole feed, so the guard may be on snapshot refreshes, not calls. Whether the snapshot is cached in L1 and L2, and what happens to a Run when it's down.
- The non-commercial clause in its terms: ask Arbeitnow, or decide the project's use fits.
- The link back it needs on screen and in `brief.md` (see `ATTRIBUTION` in `gateway/types.py`).
