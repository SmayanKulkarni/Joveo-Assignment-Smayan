# 14: The Customer Profile shapes a Run

**What to build:** A Customer's second Run asks fewer Clarifying Questions, starts with hints from what worked, and compares itself with their earlier Run. All of it is visible, and the CSM can opt out. [How a Customer Profile shapes a Run](../../resume-accounts-sources/final-decisions.md#how-a-customer-profile-shapes-a-run) is the spec.

**Blocked by:** 04: Customer Recommendation as its own deliverable; 11: A Resume drafts the Run; 13: Customer Profile

**Status:** done

- [x] The Controller copies the profile into a defaulted `profile` input field at the start; a Run with "Use profile" unticked gets none
- [x] After the model, `intake` code fills only null fields, each an Assumption with reason "from Customer Profile", in the order typed, Resume, profile
- [x] `clarity_check` skips the Noul for those fields
- [x] `plan` gets the earlier titles as hints, and the plan approval Pause marks what came from the profile through `from_profile`
- [x] Collection, relevance, the Brief and matching are unaffected
- [x] The Customer Recommendation gains one computed line against the newest earlier Run with the same folded role, country and currency, showing median Advertised pay and Sample size; it's omitted if there's no such Run
- [x] The Run Notes have one "From the Customer Profile" group
- [x] `preferences` is removed from the future-scope doc
- [x] An integration test with fakes: a second Run for one Customer asks fewer questions and its plan shows the hints; a typed value is never overridden
