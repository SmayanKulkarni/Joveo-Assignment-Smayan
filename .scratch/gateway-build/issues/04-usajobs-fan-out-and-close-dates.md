# 04: USAJOBS, fan-out and close dates (pass 2)

**What to build:** a `us` Fetch returns Adzuna and USAJOBS Postings merged and coalesced, while other countries call Adzuna only. One source failing still returns the other. Postings past their close date never reach a stage, and L1 rows whose Postings have all closed get deleted. Spec: [Gateway LLD](../../../docs/lld/gateway.md) §4, §5, §7.3, §7.4, §8, §12, §16 pass 2 steps 1-3.

Tests use the fixtures and spend no live quota. Out of scope: L2 (ticket 05), and keeping federal pay apart from Adzuna salaries (Analysis).

**Blocked by:** 03: Replay, tracing and live smoke, because replay rows must skip the close-date filter and the purge.

**Status:** done

- [x] Test: on the USAJOBS search fixture, the description starts with `JobSummary`, `:443` is gone from `url`, and `SY` gives `salary=None`
- [x] Test: FAA's 1,176 locations give region `("US",)`, and two Virginia sites give `("US", "Virginia")`
- [x] Test: a blank description and an unparseable `posted_at` are drops, and an unparseable `closes_at` is `None`
- [x] Test: the Domain table applies series overrides over families, including `8999` to `maintenance-jobs`, and an unknown series gives `None`
- [x] Test: `DatePosted` is capped at 60, `Radius` is `radius_km` in miles rounded up, and `Fetch.category` isn't sent
- [x] Test: a USAJOBS `429` is `SourceUnavailable` with no lockout, and USAJOBS reports `calls_left=None`
- [x] Test: `country == "us"` calls both sources concurrently, and other countries call Adzuna only
- [x] Test: one source failing fills `failures` and still returns the other
- [x] Test: a `SourceRejected` from one source wins over a result from the other
- [x] Test: a re-announced ad collapses, while NAVSEA's two offices (different duties) and FAA FV/FG stay apart, through `coalesce`
- [x] Test: an expired Posting is filtered on hits and fresh responses, and isn't counted in `dropped`
- [x] Test: `_purge()` runs after a live write and deletes an L1 row only when all its Postings have closed
- [x] Test: a replay row skips both the filter and the purge
