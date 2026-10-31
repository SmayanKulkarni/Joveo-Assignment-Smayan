# The Stat catalogue

Type: grilling (delegated to the agent)
Status: resolved
Assignee: smayankulkarni05
Blocked by: 02, 05, 06

## Question

Which Stats exist, with which ids and which rules, so the Brief can cite every figure it uses? Kernel §3 leaves the catalogue to Analysis.

## Answer

The catalogue is in the LLD §8. These are the decisions behind it.

**Rank skills by distinct employers, then Postings.** Booz Allen's shared opening paragraph put `IoT` and `cancer research` near the top of a data engineer's raw counts. Counting employers first demotes one company's boilerplate without any boilerplate detection. The label shows both ("Python: 15 of 100 extracted Postings, from 9 employers").

**Must-have and nice-to-have are separate counts per skill.** Most Adzuna snippets are too short to state which, so `unstated` is common and neither count is forced.

**Employer type is decided per employer, not per Posting.** The probe's Booz Allen split of 9 to 14 is the model reacting to one Posting's wording, not a fact about Booz Allen. Rule, in order:
1. USAJOBS: direct.
2. The name has "staffing" or starts a word with "recruit", or is in a short `KNOWN_AGENCIES` list: agency. The probe called Randstad direct, and a list is cheap, exact and easy to explain.
3. Otherwise the majority of that employer's Extractions, with a tie or nothing known giving `unknown`.

**Employers group by folded name minus legal suffixes** (Inc, LLC, Ltd, Pvt and so on), shown in the most common spelling. `coalesce` already treats company names as words, but the suffix rule is new because grouping needs it and Duplicates don't.

**Titles group by folded title only.** Stripping locations or levels from a title with code would also damage real variants like "Data Engineer - Java", and the variants employers really use are what the spec asks for.

**The trend is a labelled comparison, computed only when it can mean something.** The newest 14 days against the 14 before, needing `max_days_old >= 28` and at least 20 Postings across both. Rising at ≥ 1.25×, falling at ≤ 0.8×, otherwise flat. Its label says it counts ads still live, because filled ads vanish and that always tilts the view towards recent. A Caveat doesn't add more than the label, and the Brief quotes labels.

**"Now" is the newest `fetched_at`,** the same reasoning as Collection's Old data Caveat: a clock would change Stats and miss every LLM cache entry downstream on replay.

**Shares carry their percentage in the label,** because the Brief may not compute figures. **Every Stat's Evidence is the Postings it counted,** including each median's group.

**Rounding** is fixed so replay stays byte-identical: pay to whole units, shares to 3 places. Quartiles use `statistics.quantiles(n=4, method="inclusive")`, since `exclusive` can land outside the data on small groups.

**`focus` changes nothing here,** as Request & Plan §8 already says. Every Stat is cheap Python, and the Brief does the emphasis.
