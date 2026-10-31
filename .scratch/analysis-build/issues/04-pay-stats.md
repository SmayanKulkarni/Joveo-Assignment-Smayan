# 04: Pay Stats

**What to build:** `MarketStats` gains compensation: advertised, estimated and federal pay as three groups that never mix, annualised and shown in one currency, with seniority slices and the disclosed and estimated shares. The Caveats say what was estimated, assumed, excluded or converted. Spec: [Analysis LLD](../../../docs/lld/analysis.md) §8 catalogue compensation rows, §9, §10, §13 step 6 and the rest of step 8.

**Blocked by:** 03: Demand, skills, competition and title Stats, because this extends `compute_stats`.

**Status:** done

- [x] `UNITS_PER_USD` holds the 13 Adzuna currencies from ECB reference rates, with `FX_DATE`
- [x] A figure is the midpoint of `min` and `max` or the one bound, annualised with `ANNUAL`, then converted to the Stat currency
- [x] The Stat currency is `hiring_request.currency` when the table has it, otherwise `ADZUNA_CURRENCY[current_plan.country]`
- [x] For an `unknown` period only, a figure below the equivalent of 1,000 USD a year, or below a sixth of its group's median, is excluded and counted
- [x] Quartiles use `statistics.quantiles(figures, n=4, method="inclusive")`, and pay rounds to whole units
- [x] `unit` is like `"USD/year"`, and labels name the group, the count and any conversion
- [x] Seniority slices exist for `advertised` and `estimated` only
- [x] `comp.disclosed_share` counts `advertised` over Adzuna Postings, and `comp.estimated_share` is the same over `estimated`

Tests:

- [x] Each period annualises
- [x] The three groups never mix
- [x] A figure of 25 with an `unknown` period is excluded
- [x] A monthly figure is excluded by the sixth rule, and a real junior figure isn't
- [x] Conversion and the currency fallback
- [x] 4 figures give no Stats, and 5 do
- [x] The seniority slices, with the same Minimum per level

Caveats, each with a trigger and a non-trigger test:

- [x] Pay is estimated: `estimated` Stats exist and `advertised` ones don't
- [x] Too little pay data: no group reached 5 figures
- [x] Pay period assumed: any `advertised` figure had an `unknown` period, with the count
- [x] Implausible pay excluded: any figure was excluded, with the count
- [x] Pay converted: the Stat currency differs from a Posting's, with `FX_DATE`
- [x] Currency unavailable: the requested currency isn't in the table
