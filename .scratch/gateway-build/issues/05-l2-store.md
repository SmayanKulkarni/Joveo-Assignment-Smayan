# 05: L2 store (pass 2)

**What to build:** on an L1 miss, an Adzuna Fetch is answered from stored Postings when they can fill the page without skewing the Sample, spending no budget. A failed live call falls back to whatever partial page L2 has, and Collection still learns the source failed. Stored Postings expire 7 days after Adzuna last returned them. Spec: [Gateway LLD](../../../docs/lld/gateway.md) §4 steps 3 and 5, §11, §12, §16 pass 2 steps 4-5.

Adzuna only. Whether an L2 answer's age raises a Caveat is Collection's.

**Blocked by:** 04: USAJOBS, fan-out and close dates, for the source loop and `_purge()`.

**Status:** done

- [x] `CacheStatus` gains `store`, and an L2 answer reports `total` as L2's match count, `dropped=0`, `fetched_at` as the oldest `last_seen_at` served, and the current `calls_left`
- [x] Test: each live Adzuna response, from any page, is written before `coalesce` with the newest version winning, and `via` and `last_seen_at` are updated
- [x] Test: the four rows of the reuse table in §11 give the stated result
- [x] Test: the Posting checks hold for title words, `posted_at` within `max_days_old`, `domain` against `category`, and a country-wide `via` against a `region` segment
- [x] Test: page N is served only when its slice is full, otherwise the call goes live
- [x] Test: a read-before-call hit spends no budget
- [x] Test: on a failed live call, a partial page fills both `sources[adzuna]` and `failures[adzuna]`, and with no matches only `failures[adzuna]`
- [x] Test: an L2 answer isn't written to L1, and during recording is written to the replay file
- [x] Test: a replay hit returns before L2
- [x] Test: USAJOBS Postings are never stored in L2
- [x] Test: a row that no longer validates is skipped
- [x] Test: rows past `l2_fresh_days` are hidden on read and deleted after the next live write, and serving from L2 doesn't move `last_seen_at`
- [x] The read carries the `ponytail:` comment naming the 8,750-row ceiling and the upgrade path
