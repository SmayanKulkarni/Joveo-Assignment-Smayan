# 01: Prefactor and the Brief contract

**What to build:** everything the Brief stage needs from the rest of the codebase is in place, and a Run on stubs still reaches `done` holding a Market Brief with the real shape. Spec: [Brief LLD](../../../docs/lld/brief.md) §2, §3, §15 pass 1 step 1.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `fold` and `employer_key` live in the kernel and Analysis imports them, with Analysis's tests unchanged and green, so Brief needn't import a stage
- [x] Analysis's two Caveats read "fewer than 5 advertised salaries" and "no pay group has 5 salaries", since "reached 5 figures" was read as money
- [x] `MarketBrief` and its parts, `BriefDraft`, `BriefRevision` and `InsightVerdict` have the fields in §3, and `BriefDraft` fields each carry a description
- [x] `State` gains `brief_draft`, `critic_verdicts` and `revisions`, owned by Brief
- [x] A `stub_brief()` test helper replaces `MarketBrief()`, and the tests that build one are updated
- [x] All the new models survive the serde test from Runtime §16, and compile allowlists them
- [x] The stub Run still reaches `done`
