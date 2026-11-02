# 12: Ranked Matches

**What to build:** A Run with a Resume ends with ranked Matches in the Customer Recommendation, each showing its score, Level, matched and missing skills, and a link to the Posting. [Matching Postings to a Resume](../../resume-accounts-sources/final-decisions.md#matching-postings-to-a-resume) is the spec, including the exact rules for matched skills, score, Level and ranking.

**Blocked by:** 02: Remote Postings; 03: Guardrails on Postings; 04: Customer Recommendation as its own deliverable; 11: A Resume drafts the Run

**Status:** done except tuning the constants on three fictional Resumes against recorded Postings, and recording the chosen values (needs the Resumes and a choice of recorded Postings)

- [x] A `match` node owned by Analysis runs `stats → match → write_brief`, including on an empty Sample, with no LLM or Jev call
- [x] Any exception logs the Caveat "Matches unavailable", which holds no Resume content, and the Run carries on
- [x] Resume skill names join the `normalise_skills` input after the 300-name cut, and a Run with no Resume sends the same prompt as today
- [x] Matched skills, score (with the floor of 5), Level, ranking and the default view follow the spec, with its numbers as constants
- [x] Postings with no Extraction are counted in the Run Notes, not scored
- [x] A Match shows both spellings when they differ, and "added by CSM" where it applies
- [x] A row shows rank, title, employer, place, pay with its Advertised or Estimated label, score, Level, skills, attribution and link
- [x] Remote and partial-advert labels appear on the row and in the download, and neither changes the score
- [x] "Show the other N" reveals the rest, and if none pass the Recommendation says so
- [x] `match` is in the stubs, demo, topology and stage strip
- [ ] The stuffed-Posting fixture and table tests cover every rule; the constants are tuned on three fictional Resumes against recorded Postings, and the chosen values recorded
