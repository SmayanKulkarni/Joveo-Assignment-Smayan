# Normalising pay

Type: grilling (delegated to the agent)
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01

## Question

Settle the HLD §12 items: currency and period normalisation, `salary_is_predicted`, and USAJOBS vs Adzuna in compensation Stats.

## Answer

**Three groups, never pooled.** Each gets its own median and middle 50%.

| Group | Which Postings | Why apart |
|---|---|---|
| `advertised` | Adzuna, not `predicted` | What employers actually said |
| `estimated` | Adzuna, `predicted` | Adzuna's own model, not an employer's statement. All 100 fixture salaries are this |
| `federal` | USAJOBS | Fixed pay tables, which the Gateway LLD and HLD §7 say must never mix into market pay. Also wide GS ranges |

Dropping estimates would leave a US Brief with no pay figure at all. Pooling them would present a model's guess as market evidence. Keeping them labelled gives the Brief a figure and an honest strength. ⏳ The Brief LLD decides how a Client Recommendation uses them, with the expectation of preferring `advertised` and a lower Confidence Tag on `estimated`.

**The disclosure share counts advertised only, over Adzuna Postings.** An estimated salary isn't disclosed pay, and counting USAJOBS would make any federal-heavy Sample look transparent because the law requires it.

**A Posting's figure:** the midpoint when both bounds exist, otherwise the one bound.

**Period:** annual, as ×2080 hourly, ×260 daily, ×52 weekly, ×26 biweekly, ×12 monthly. `unknown` (every Adzuna salary) is read as annual, the evidence for estimates being the fixtures. A Caveat fires when advertised pay relied on that reading.

**Implausible figures,** for `unknown` periods only, are excluded and counted, because an hourly rate read as annual would wreck a group:
- below the equivalent of 1,000 USD a year, which catches hourly and most low monthly figures, or
- below one sixth of the group's median, which catches monthly figures (a ratio of 12) while leaving real junior pay alone.

**Currency:** a Run has one country and so one market currency, and USAJOBS is USD inside a US Run. The Stat currency is `hiring_request.currency` when the table has it, otherwise the market currency. If the user asked for a currency the table lacks, a Caveat says so and pay stays in the market currency.

**A fixed `UNITS_PER_USD` table with a date, not a live rate lookup.** It covers the 13 Adzuna currencies, all in the ECB's reference rates. A live call adds a dependency and a failure mode, and would change Stats on replay. Pay is rounded to whole units, so the conversion doesn't suggest false precision. A Caveat states the date whenever a conversion happens, and rates are refreshed by hand.

**Minimums:** a group needs 5 figures, below which it has no Stats rather than a misleading median. The same applies per seniority level, so `comp.estimated.senior.median` exists only with 5 or more figures. That per-level split is what lets a "Senior Data Analyst" Brief recommend senior pay, even though Relevance deliberately keeps every level in the Sample.
