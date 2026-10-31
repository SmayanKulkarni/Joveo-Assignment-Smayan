# Write docs/lld/brief.md

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 13

## Question

Write `docs/lld/brief.md` from the resolved tickets, and bring the HLD, Kernel, Runtime, Analysis, Collection, Request & Plan, glossary and future-scope docs into line with it, including the missing glossary entry for Client Recommendation. This records decisions the user has made and makes none of its own.

## Answer

Written to [docs/lld/brief.md](../../../docs/lld/brief.md). Unlike the question assumed, the decisions it records were made by the agent, on the user's instruction.

Brought into line:

| Doc | Change |
|---|---|
| HLD | §5 the writer cites Stat ids, §6 the critic judges against Stats, §12 the Brief row gone |
| Kernel | §4 the three `State` fields, §6 and §7 the revision loop and route, §12 the critic isn't an LLM call, §14 the banner |
| Analysis | §14 "`estimated` at a lower tag" replaced: a reason says when pay is estimated |
| Collection, Request & Plan, Gateway, Runtime | ⏳ Brief items now point to the LLD. Runtime's stub writes `stub_brief()` |
| Future scope | A Brief section |
| Glossary | Client Recommendation added, and Hiring Outlook says it's an estimate |

The Gateway wasn't in the question's list, but held two ⏳ Brief items.

No code changed. The two Analysis Caveats, the move of `fold` and the `State` fields are step 1 of the LLD's build checklist.
