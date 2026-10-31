# 03: Demand, skills, competition and title Stats

**What to build:** a real `stats` node turns Extractions into `MarketStats`, with Evidence on every Stat, so every number traces to the Postings it counted. Python computes everything, and two runs on the same state give identical Stats. Pay comes in the next ticket. Spec: [Analysis LLD](../../../docs/lld/analysis.md) §8 (all but pay), §10, §13 step 7, the matching part of step 8 and the Evidence half of step 9.

**Blocked by:** 01: Postings become grounded Extractions. Tests set `skill_aliases` by hand, so this doesn't need 02.

**Status:** ready-for-agent

General rules:

- [ ] `compute_stats(state)` returns the Stats, the Caveat messages and the summary data, and the node writes them to `stats` and `run_log`
- [ ] Ids, Minimums and omissions follow the §8 catalogue for the demand, skills, competition and titles_seniority rows
- [ ] "Now" is the newest `fetched_at`, never the clock
- [ ] Stats from Extractions use the Sample keys with an Extraction as their denominator, and their labels say so
- [ ] Shares carry their percentage in the label and round to 3 places
- [ ] A Sample of zero gives `MarketStats(sample_size=0, stats=[])`
- [ ] Test: "now" comes from `fetched_at`, and two runs give identical Stats
- [ ] Test: every Stat's Evidence is within the Sample

Skills:

- [ ] Names resolve through `skill_aliases`, with `must` winning over `nice` over `unstated`, and a skill with no alias shows in its most common spelling
- [ ] Ranked by distinct employers, then Postings, then name, and a Posting with no company counts as its own employer
- [ ] The label shows both counts
- [ ] Test: an alias and its canonical name in one Posting count once
- [ ] Test: skills rank by employers before Postings

Employers and titles:

- [ ] Employers group on the folded name without trailing legal suffixes, and Postings with no company count only towards `.unknown_share`
- [ ] Employer type is decided per employer in the §8 order, using `KNOWN_AGENCIES`
- [ ] Titles group by folded title only
- [ ] Test: a Booz-style split resolves by majority, and a tie is `unknown`
- [ ] Test: Randstad is an agency with any model answer, and USAJOBS is direct

Trend:

- [ ] Compares the newest 14 days against the 14 before that, and the label carries the live-ads wording
- [ ] Test: the minimums (`max_days_old >= 28`, 20 Postings across both windows) and the thresholds (1.25×, 0.8×, and `rising` with an empty older window)

Caveats and the Run log, each Caveat with a trigger and a non-trigger test:

- [ ] Postings not extracted: any Sample key has no Extraction, with the count
- [ ] Skills from snippets: any Adzuna Posting in the Sample, with the count
- [ ] One `note` holds the Sample size, Extractions, Stats produced and skills dropped as `ungrounded`
