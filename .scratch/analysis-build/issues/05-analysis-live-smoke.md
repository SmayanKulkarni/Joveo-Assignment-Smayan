# 05: Analysis live smoke

**What to build:** a script runs fixture Postings through the real model and prints what Analysis made of them, which proves the whole stage and shows any bad merge. It spends no job API calls. Spec: [Analysis LLD](../../../docs/lld/analysis.md) §7, §11, §13 step 10.

**Blocked by:** 02: Skill spellings merge into canonical names, 03: Demand, skills, competition and title Stats, and 04: Pay Stats.

**Status:** done

- [x] `scripts/smoke_analysis.py` (not in CI) runs fixture Postings through `minimax/minimax-m3.1-flash`
- [x] It prints the top skills, every merge and the employer types
- [x] It asserts that `AWS` and `S3`, and `Git` and `GitLab`, stay apart when both appear
- [x] Results and any change to the prompts are recorded in this ticket for the write-up

## Results

Run on 2026-10-31 with `minimax/minimax-m3.1-flash` on both tiers, replay off, over `tests/fixtures/jobs/` (100 Adzuna, 25 USAJOBS, no job API calls). `python scripts/smoke_analysis.py [model]` takes about 15 s: 10 Batches, 125 Postings, 63 to 77 skills dropped as ungrounded per run. Extraction was 119, 125, 125 and 120 of 125 Postings across the runs. The script now prints any Batch that returns nothing; the 120 run printed none, so the model skipped Postings inside Batches that did return, and the 119 run's cause was not captured.

- **Merge prompt over-merged.** With the LLD's wording, the cap of 300 names gave 79 merges, many wrong: `t sql` and `pl sql` into `sql`, `aws` into `aws cloud services`, `flight dynamics` and `statics` into one, `llms` into `generative pretrained transformers gpts`, `engineer in training eit` into `fundamentals of engineering fe`. The earlier probe (166 names, 12 merges) did not show this. This run sent a longer list and a wider fixture set (including USAJOBS engineering Postings); which of those, or model variance, caused it was not isolated.
- **Prompt change** (`MERGE_SYSTEM` in `analysis/prompts.py`): added "Most names belong to no group, so expect only a handful of groups" and named three failing shapes ("pl sql" and "sql", "flight dynamics" and "statics", "aws" and "aws cloud services") as not spellings of each other. Two of the examples repeat the SQL and AWS rule above and one is specific to the USAJOBS fixtures, so a run without the examples was tried: it gave 52 merges, including `t sql → sql` and `secret → top secret sci clearance`. The examples stay. The next run gave 17 merges, mostly correct (`airflow`, `spark`, `azure`, `glue`, `etl`, `nlp`). This is one run per wording, so the improvement is a direction, not a measured rate.
- **Assertions pass** on the last run after the change (the output of the first post-change run was not read): `AWS` and `S3` stay apart, `Git` and `GitLab` stay apart (both pairs appear in this Sample; on the first run `Git` and `GitLab` did not both appear, so that check was skipped).
- **Employer types** came out at about 50% direct and 49% agency, with 2 Postings of unknown type. Not checked against the individual employers here.
- **Reciprocal and chained aliases** (`data analytics → analytics` with `analytics → data analytics`) left a skill split under two keys. `_aliases` now aims each group at the end of any chain, so neither can form; one test covers it.
- **Remaining weak spot:** `spark pyspark → pyspark` still gets through.
- **Step 11** (is an `unknown` pay period on advertised Adzuna pay annual) was unproven here because the fixtures have only estimated pay; ticket 06 checked it on a live Run and it is annual.
