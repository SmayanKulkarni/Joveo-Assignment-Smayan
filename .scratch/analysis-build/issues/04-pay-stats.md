# 04: Pay Stats

**What to build:** `MarketStats` gains compensation: advertised, estimated and federal pay as three groups that never mix, annualised and shown in one currency, with seniority slices and the disclosed and estimated shares. The Caveats say what was estimated, assumed, excluded or converted. Spec: [Analysis LLD](../../../docs/lld/analysis.md) §8 catalogue compensation rows, §9, §10, §13 step 6 and the rest of step 8.

**Blocked by:** 03: Demand, skills, competition and title Stats, because this extends `compute_stats`.

**Status:** ready-for-agent

- [ ] `UNITS_PER_USD` holds the 13 Adzuna currencies from ECB reference rates, with `FX_DATE`
- [ ] A figure is the midpoint of `min` and `max` or the one bound, annualised with `ANNUAL`, then converted to the Stat currency
- [ ] The Stat currency is `hiring_request.currency` when the table has it, otherwise `ADZUNA_CURRENCY[current_plan.country]`
- [ ] For an `unknown` period only, a figure below the equivalent of 1,000 USD a year, or below a sixth of its group's median, is excluded and counted
- [ ] Quartiles use `statistics.quantiles(figures, n=4, method="inclusive")`, and pay rounds to whole units
- [ ] `unit` is like `"USD/year"`, and labels name the group, the count and any conversion
- [ ] Seniority slices exist for `advertised` and `estimated` only
- [ ] `comp.disclosed_share` counts `advertised` over Adzuna Postings, and `comp.estimated_share` is the same over `estimated`

Tests:

- [ ] Each period annualises
- [ ] The three groups never mix
- [ ] A figure of 25 with an `unknown` period is excluded
- [ ] A monthly figure is excluded by the sixth rule, and a real junior figure isn't
- [ ] Conversion and the currency fallback
- [ ] 4 figures give no Stats, and 5 do
- [ ] The seniority slices, with the same Minimum per level

Caveats, each with a trigger and a non-trigger test:

- [ ] Pay is estimated: `estimated` Stats exist and `advertised` ones don't
- [ ] Too little pay data: no group reached 5 figures
- [ ] Pay period assumed: any `advertised` figure had an `unknown` period, with the count
- [ ] Implausible pay excluded: any figure was excluded, with the count
- [ ] Pay converted: the Stat currency differs from a Posting's, with `FX_DATE`
- [ ] Currency unavailable: the requested currency isn't in the table
