# 02: Remote Postings

**What to build:** A remote Arbeitnow Posting reaches a Run in any country, counts as a full member of the Sample, and is clearly labelled. Items 9 to 14 of [Choosing among the search tools](../../resume-accounts-sources/issues/12-choosing-among-many-search-tools.md) are the spec.

**Blocked by:** 01: Arbeitnow Postings in a Run

**Status:** done

- [x] `Posting.remote` defaults to false, so existing checkpoints still load
- [x] The Arbeitnow mapper sets it from the `remote` flag, the location or a tag; Adzuna and USAJOBS stay false
- [x] A remote Posting skips the country and location filters in every Arbeitnow Fetch; title and age still apply
- [x] Its `region` is `("Remote",)`, and the places chart is tested with a Sample holding that region
- [x] The "Includes remote" Caveat fires whenever any are present
- [x] Remote Postings count toward Sufficiency and every Stat, and pay Stats are unaffected

## Built

- `glance._places` labelled a one-element region "Area not given", so the Remote group needed a fix there: remote Postings now form a "Remote" group. This is the case ticket 12 said wasn't re-checked.
