# 06: Check the advertised pay period assumption

**What to build:** on a live Run with real advertised Adzuna pay, confirm that an `unknown` period really is annual. The fixtures only hold estimates, so this is unproven until then, and the "Pay period assumed" Caveat states the assumption in the meantime. Spec: [Analysis LLD](../../../docs/lld/analysis.md) §9, §13 step 11.

**Blocked by:** 05: Analysis live smoke.

**Status:** done

- [x] It spends Adzuna calls, so get the user's OK in chat before running it, and it can share a Run with Delivery's sample runs
- [x] Advertised figures with an `unknown` period from a live Run are inspected and recorded in this ticket
- [x] If they aren't annual, the `ANNUAL` rule and the Caveat text change, with a test (they are annual, so no change)

## Results

Run on 2026-10-31 with the user's OK for 3 Adzuna calls: one page of 50 each for `data engineer` (us), `warehouse associate` (us, chosen because its pay is mostly hourly) and `software engineer` (gb), country-wide, 30 days. Every `advertised` (non-predicted) salary came back with `period="unknown"`, as the mapper sets it. Adzuna's response carries no period field, so the check is on the magnitudes.

- **Annual, confirmed.** 60 advertised figures in usable ranges, all annual-sized: US data engineers 70,000 to 200,000 USD; GB software engineers 45,000 to 120,000 GBP.
- **Hourly pay arrives already annualised.** The 20 US warehouse figures run 20,800 to 66,560, and the common ones are exact multiples of 2,080 (20,800 = 10/h, 31,200 = 15/h, 41,600 = 20/h, 52,000 = 25/h). So Adzuna converts hourly to annual itself, and `ANNUAL[unknown] = 1` is right. Applying the hourly factor again would have been wrong.
- **Junk does appear, and the existing rule catches it.** Four GB postings had a lone `max` of 5.0 or 60.0 (an hourly or day figure that was not annualised). Against GB medians of about 65,000 they fall below both the 1,000 USD floor and a sixth of the group median, so step 4 excludes them and the "Implausible pay excluded" Caveat counts them. Not run through `stats` live, only checked against the rule by reading it.
- **Outliers kept:** `348000` USD for a cleared role (its title says `$348k/yr`) and a GBP 208,000 to 286,000 director are real, so nothing to change.
- **Changes:** none to `ANNUAL` or the Caveat text. The LLD §9 "unproven" note now says it was checked. The Caveat still reads "treated as annual", which is now an observed fact rather than a guess, but it stays because it tells a reader the period is inferred, not stated.
- **Not covered:** one page per query, two countries, and Adzuna's other 11 countries were not sampled. The Adzuna budget for the day is down to 1 call.
