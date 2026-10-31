# 05: Client Recommendations

**What to build:** the Brief recommends a job title, a salary band and the top skills, all computed by code with their reasons and Evidence, and each left out on its own when it lacks evidence. Spec: [Brief LLD](../../../docs/lld/brief.md) §8, §15 pass 1 step 4.

**Blocked by:** 02: A zero-Posting Run produces a real Brief

**Status:** done

- [x] Titles need `MIN_TITLE_POSTINGS` from `MIN_TITLE_EMPLOYERS`, so a one-employer title is excluded, and rank by employers, then Postings, then id, with a title holding the request's level words first
- [x] A test pins the title name split against a real Analysis label, since `Stat` has no name field
- [x] The band uses the first of advertised then estimated, with federal only when over half the Sample is USAJOBS, and that group's slice for the request's level or otherwise the whole group
- [x] The band runs `.p25` to `.p75` with the Stat's unit, and cites `.p25`, `.median` and `.p75`
- [x] The reason names the figure count, group and level, says estimated pay is Adzuna's estimate rather than stated pay, and says federal pay follows fixed tables
- [x] Top skills are the first `TOP_SKILLS` of `skills.*.count` with `MIN_SKILL_EMPLOYERS` each, and the reason notes snippets when an Adzuna Posting is in the Sample
- [x] Each recommendation is `None` on its own when evidence is missing, and the Brief and Markdown show the real values
