# 11: A Resume drafts the Run

**What to build:** A CSM can start a Run with little or nothing typed, and the Customer's Resume fills in the title, seniority and place. Each one shows up as an Assumption at plan approval. Items 5, 6 and 10 of [What a Resume is for](../../resume-accounts-sources/issues/17-what-a-resume-is-for.md) are the spec.

**Blocked by:** 09: Runs belong to a Customer; 10: Upload and correct a Resume

**Status:** done (see commit)

- [x] The Controller copies the current facts into a defaulted `resume` input field, so later uploads don't change a Run
- [x] `intake` reads the request and the facts, and whatever the CSM typed takes priority
- [x] Each field taken from the Resume is an Assumption; `clarity_check` still asks about whatever is unclear
- [x] All three Pauses stay
- [x] The New Run screen says "Using the Resume uploaded on <date>"
- [x] The Run Notes gain one line naming when the Resume was uploaded and which CSM-added facts were used
- [x] `write_brief` never receives Resume facts
- [x] A test asserts a Run's prompts contain nothing from a second Customer's Resume, and that nodes have no database access to fetch one
