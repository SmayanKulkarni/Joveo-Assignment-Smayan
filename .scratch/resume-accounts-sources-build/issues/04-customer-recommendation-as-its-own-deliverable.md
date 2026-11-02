# 04: Customer Recommendation as its own deliverable

**What to build:** A finished Run shows two deliverables in two tabs: the Market Brief about the market, and a Customer Recommendation with the job title, salary band and top skills to aim for. This works before any Resume exists, and says why there are no Matches. Items 2 to 4 of [What a Resume is for](../../resume-accounts-sources/issues/17-what-a-resume-is-for.md) and the Two deliverables line of [the screens](../../resume-accounts-sources/final-decisions.md#resume-profile-and-sign-in-screens) are the spec.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] The old Client Recommendation data moves out of the Market Brief into a Customer Recommendation, with its Evidence
- [x] `customer_recommendation` and `recommendation_markdown` are defaulted State fields owned by Brief, and the new models are in the checkpoint allowlist
- [x] Old finished Runs whose Brief still holds the old data still open
- [x] Hiring Outlook keeps its three values and its logic, and gains one fixed line per value on what it means for a job seeker
- [x] The Recommendation has its own tab and downloads; the system sends nothing to anyone
- [x] With no Resume, the Run Notes and the tab say why there are no Matches
- [x] The term Client is gone from code, UI and docs the change touches
- [x] Python and Vitest tests cover both tabs, the downloads and an old Run
