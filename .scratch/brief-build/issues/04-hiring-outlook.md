# 04: Hiring Outlook

**What to build:** the Brief rates how hard the role looks to hire for, from employers, how demanding the profile is and the trend, and always says it's a proxy because Postings don't show candidates. Spec: [Brief LLD](../../../docs/lld/brief.md) §7, §8 (the request's level), §15 pass 1 step 3.

**Blocked by:** 02: A zero-Posting Run produces a real Brief

**Status:** done

- [x] Each row of the §7 table gives its rating, first match winning
- [x] A falling trend blocks Hard to fill and a rising trend blocks Favourable, and the trend never decides a rating by itself
- [x] An unknown bar can't reach Favourable, and a stated senior level makes a high bar
- [x] The request's level comes from the word table in §8, and anything else is no level
- [x] `stat_ids` are the Stats that decided it and Evidence is their union, both empty at the default
- [x] Every reason states that Postings show demand rather than candidates, and the default says it's a default rather than a finding
- [x] Identical Stats give an identical result, and the Brief and Markdown show the rule's rating and reason
