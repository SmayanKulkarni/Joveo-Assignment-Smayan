# Hiring Outlook rules

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01

## Question

How is exactly one of Favourable, Competitive or Hard to fill chosen, and who writes its one-line reason? The spec defines the values by talent relative to demand, but Postings only measure demand, so which Stats stand in for supply, and how does the Brief say so honestly? What happens when the Sample is too thin to support any of the three?

## Answer

Decided by the agent, on the user's instruction to make every decision on this map. **Code picks the rating and writes the reason,** and `BriefDraft` gains no field. The first probe's LLM gave different ratings on identical input, and said favourable with no Postings.

**Nothing stands in for supply.** Postings don't show candidates, so the rule reads demand pressure and how demanding the profile is, and every reason says so. First match wins:

| # | Condition | Rating |
|---|---|---|
| 1 | Under 20 Postings | Competitive, stated as a default and not a finding |
| 2 | 20+ employers, a high bar, and the trend isn't falling | Hard to fill |
| 3 | Under 10 employers, a known bar that isn't high, and the trend isn't rising | Favourable |
| 4 | Otherwise | Competitive |

- **Employers** is `competition.distinct_employers`. Many employers is what the spec calls "many employers chasing the same profile".
- **A high bar** is any of: the request's own level is senior, lead or executive; `skills.years_median` is 5 or more; or `seniority.senior`, `.lead` and `.executive` sum to 50% or more. The bar is **known** when the request states a level, or either kind of Stat exists. With neither, the rule can't call the talent plentiful.
- **The trend only blocks.** It can stop Hard to fill or Favourable, but never earns either, because Analysis says it tilts recent.
- **20 Postings** is the lowest target a Search Plan can have, so anything below it is weak by any plan's standard.
- **Pay isn't used.** Nothing in the Stats says what standard pay is.

**The reason** is one line, like: "61 employers across 125 Postings, with a median of 4 years asked and a rising trend. Postings show demand, not candidates, so this is an estimate of the talent market." The default reads: "Only 8 Postings, too few to judge the talent market, so Competitive is a default rather than a finding."

**The enum stays at three values.** The spec says exactly one, and `outlook` is required. A fourth "not rated" would be more exact but breaks that, so the honesty lives in the reason.

**The writer sees a rule-based rating so the Summary can't contradict it, and never sees the default,** since [Live check of the draft design](13-live-check-of-the-draft-design.md) showed it repeats a default as a finding. The rule is one pure function called by both `write_brief` and `render`, with no new `State` field.

**Evidence** is the union of the Stats that decided it. A default has none, which `stat_ids=[]` makes plain.

Checked on the fixtures in that same ticket: Competitive at 125, Hard to fill at the Adzuna 100, whose median is one year higher, and a default at 8. These are judgement calls, not tuned, and Favourable will be rare: since Postings can't see plenty of talent, the rule leans to Competitive. That belongs in the write-up's failure modes.
