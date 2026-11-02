# 17: Name Arbeitnow on the search step

**What to build:** The "Search job boards" Step names all three sources. Ticket 01 added Arbeitnow, and `SOURCES` in `run/steps.ts` already maps `search_arbeitnow`, but the idle Step still says "Adzuna, USAJOBS".

**Blocked by:** None (can start immediately)

**Status:** done

- [x] The `sub` of the `search` Step in `web/src/run/steps.ts` reads "Adzuna, USAJOBS, Arbeitnow"
- [x] `steps.test.ts` has a case where a `search_arbeitnow` tool call lights the `search` Step and names Arbeitnow, so the mapping stays covered
