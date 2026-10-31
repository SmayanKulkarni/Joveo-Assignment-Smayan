# Client Recommendations

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 02

## Question

How are the suggested job title, salary band and top skills chosen, and how is each tied to Evidence? Which pay group may set the band (Analysis expects `advertised`, then `estimated` at a lower tag, and never `federal` alone for a private-sector role), which seniority slice fits the request, and what is recommended when no pay group has enough figures?

## Answer

Decided by the agent, on the user's instruction. **Code chooses all three and writes each reason,** so `BriefDraft` gains nothing. The first probe's LLM left these empty or put prose in them, and each is a pick from Stats.

**The request's level** comes from words in `hiring_request.seniority`, first match: junior, entry, graduate, intern → `entry`; mid → `mid`; senior, sr → `senior`; lead, principal, staff → `lead`; director, head, vp, chief, executive → `executive`. Anything else, such as "5+ years", is no level.

**Job title:**
- Candidates are `titles.variant.*` with at least 3 Postings from at least 2 employers, so one company's repeated ad can't win.
- Ranked by distinct employers, then Postings, then id, as Analysis ranks skills.
- With a request level, a candidate whose title has one of that level's words wins over one without.
- The name is the Stat's label before its last ": ", which a test pins, since `Stat` has no name field.

**Salary band:**
- **Group:** `advertised`, then `estimated`. `federal` only if over half the Sample is USAJOBS, the same fact as the Mostly federal Caveat, since no field says whether a role is private-sector.
- **Level:** within the first group with Stats, that level's slice if it exists, otherwise the whole group, with the reason saying "all levels". A stated salary at the wrong level beats a guess at the right one: it's the group order Analysis expected, and the reason discloses it.
- **Band:** `.p25` to `.p75`, the spec's "middle 50%". The cited Stats are `.p25`, `.median` and `.p75`.
- **Tags:** none. Analysis's "`estimated` at a lower tag" no longer holds, since [Confidence Tag rules](03-confidence-tag-rules.md) tags only Insights. So the reason has to say it: "Middle 50% of 100 Adzuna-estimated figures, at senior level. These are Adzuna's estimates, not pay employers stated."

**Top skills:** the first 5 `skills.*.count` Stats in Stat order, which is already by employers, with at least 3 employers each. The reason gives Posting counts, and says skills come from snippets when any Adzuna Posting is in the Sample.

**No evidence means `None`,** for each of the three alone. Markdown then says "Not enough evidence to suggest a job title". A plan's title or an LLM's guess would have no Evidence, and the spec requires each be tied to it. When no pay group has Stats, the band is `None` and Analysis's Too little pay data Caveat explains it.

**Evidence** on each is the union of its cited Stats' Postings, expanded by `render`.

**`focus` changes none of this:** a client gets all three whatever the emphasis.
