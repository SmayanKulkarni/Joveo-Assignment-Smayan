# 06: Check the advertised pay period assumption

**What to build:** on a live Run with real advertised Adzuna pay, confirm that an `unknown` period really is annual. The fixtures only hold estimates, so this is unproven until then, and the "Pay period assumed" Caveat states the assumption in the meantime. Spec: [Analysis LLD](../../../docs/lld/analysis.md) §9, §13 step 11.

**Blocked by:** 05: Analysis live smoke.

**Status:** ready-for-agent

- [ ] It spends Adzuna calls, so get the user's OK in chat before running it, and it can share a Run with Delivery's sample runs
- [ ] Advertised figures with an `unknown` period from a live Run are inspected and recorded in this ticket
- [ ] If they aren't annual, the `ANNUAL` rule and the Caveat text change, with a test
