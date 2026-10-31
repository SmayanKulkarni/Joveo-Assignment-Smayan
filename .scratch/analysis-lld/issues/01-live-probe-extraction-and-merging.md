# Live probe of extraction and skill merging

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

Batch size, the token limit, the grounding rule and the skill-merge design all depend on how a real model behaves on real Postings. What does it do on the fixtures, and does `Send` behave as the failure policy needs?

## Answer

Run on 2026-10-31 from throwaway scratchpad scripts, using `tests/fixtures/jobs/` (100 Adzuna, 25 USAJOBS), `minimax/minimax-m3.1-flash` through the real `Tiers.structured`, and `typesafe/jev-1.14`. No Adzuna or USAJOBS calls.

**Batch size**

| Batch | `max_tokens` | Time | Tokens in / out (reasoning) | Missing | Skills not in the Posting |
|---|---|---|---|---|---|
| 10 Adzuna | 2,048 | 16 s | failed: `LLMExhausted` after 2 attempts | | |
| 20 Adzuna | 2,048 | 18 s | failed: `LLMExhausted` after 2 attempts | | |
| 20 Adzuna | 8,192 | 15 s | 2,604 / 4,092 (2,080) | 0 | 3 of 157 (1.9%) |
| 40 Adzuna | 8,192 | 30 s | 4,782 / 6,199 (2,886) | 0 | 24 of 240 (10%) |
| 5 USAJOBS, 17,101 chars | 8,192 | 3 s | 3,324 / 745 (0) | 0 | 0 of 53 |

- The cheap tier's default 2,048 tokens can't hold even 10 Postings, because reasoning takes about half the output.
- Skills not found in the cited Posting grow with Batch size, which points to attribution slipping between Postings. This is a single run per size, so it's a direction, not a measured rate.
- No Posting was missing from any response.

**Pay in the fixtures**

All 100 Adzuna salaries are `predicted`, with `min == max`, ranging from 89,379 to 363,162 USD, so `unknown` period reads as annual for estimates. No advertised Adzuna salary was available, so the same reading for advertised pay is **unproven until a live Run**. All 25 USAJOBS rows are `PA` ranges.

**Skill merging**

A first merge prompt, "group names that mean exactly the same skill", over-merged on 221 names: `AWS` took `S3`, `Lambda` and `Glue`, `Git` took `Bitbucket`, `Azure Data Factory` took `SnapLogic`, and `Machine Learning` took `Big Data`. These would inflate top-skill counts directly. The extraction prompt also returned lists as one name ("AWS: Glue, S3, Athena, Data Catalog") and duties as skills ("data engineering" 19, "pipelines").

A tightened extraction and merge prompt (say what a variant is, name what stays apart, default to leaving out, and split lists) gave 166 names and 12 proposed merges, all correct: `Airflow`→`Apache Airflow`, `Spark`→`Apache Spark`, `Azure`→`Microsoft Azure`, `data lakes`→`data lake`. Jev agreed with all 12 (p 0.79 to 0.98), so it never had to veto anything. 15 of 335 skills (4.5%) still weren't found in the cited Posting.

**Boilerplate.** `IoT` (15), `fraud detection` (9) and `cancer research` (8) reached the top of the raw counts, almost all from Booz Allen's 23 Postings, which share a standard opening paragraph.

**Employer type.** Per-Posting answers disagree within one employer (Booz Allen: 9 agency, 14 direct). Well-known staffing firms were also missed: Randstad Digital and Mitchell Martin came back direct.

**`Send`, offline, on the pinned versions.** With a Pydantic payload and 4 branches, one raising and one returning `{}`: the fan-in node runs once, a rerun re-executes only the failed branch, the finished branches' writes survive, and `{}` is a valid update. The checkpoint stores the `Send` payload class, so it needs an entry in `allowed_msgpack_modules` under strict msgpack.
