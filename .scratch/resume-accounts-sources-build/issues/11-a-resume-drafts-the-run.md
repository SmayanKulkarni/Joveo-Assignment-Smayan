# 11: A Resume drafts the Run

**What to build:** A CSM can start a Run with little or nothing typed, and the Customer's Resume fills in the title, seniority and place. Each one shows up as an Assumption at plan approval. Items 5, 6 and 10 of [What a Resume is for](../../resume-accounts-sources/issues/17-what-a-resume-is-for.md) are the spec.

**Blocked by:** 09: Runs belong to a Customer; 10: Upload and correct a Resume

**Status:** in-progress (API and graph done; the New Run screen line "Using the Resume uploaded on <date>" is not built)

- [ ] The Controller copies the current facts into a defaulted `resume` input field, so later uploads don't change a Run
- [ ] `intake` reads the request and the facts, and whatever the CSM typed takes priority
- [ ] Each field taken from the Resume is an Assumption; `clarity_check` still asks about whatever is unclear
- [ ] All three Pauses stay
- [ ] The New Run screen says "Using the Resume uploaded on <date>"
- [ ] The Run Notes gain one line naming when the Resume was uploaded and which CSM-added facts were used
- [ ] `write_brief` never receives Resume facts
- [ ] A test asserts a Run's prompts contain nothing from a second Customer's Resume, and that nodes have no database access to fetch one
