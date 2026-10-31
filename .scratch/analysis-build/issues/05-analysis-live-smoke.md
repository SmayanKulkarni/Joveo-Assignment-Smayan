# 05: Analysis live smoke

**What to build:** a script runs fixture Postings through the real model and prints what Analysis made of them, which proves the whole stage and shows any bad merge. It spends no job API calls. Spec: [Analysis LLD](../../../docs/lld/analysis.md) §7, §11, §13 step 10.

**Blocked by:** 02: Skill spellings merge into canonical names, 03: Demand, skills, competition and title Stats, and 04: Pay Stats.

**Status:** done

- [x] `scripts/smoke_analysis.py` (not in CI) runs fixture Postings through `minimax/minimax-m3.1-flash`
- [x] It prints the top skills, every merge and the employer types
- [x] It asserts that `AWS` and `S3`, and `Git` and `GitLab`, stay apart when both appear
- [x] Results and any change to the prompts are recorded in this ticket for the write-up

## Results

Run on 2026-10-31 with `minimax/minimax-m3.1-flash` on both tiers, replay off, over `tests/fixtures/jobs/` (100 Adzuna, 25 USAJOBS, no job API calls). `python scripts/smoke_analysis.py [model]` takes about 15 s: 10 Batches, 125 Postings, 63 to 77 skills dropped as ungrounded per run. The first run extracted only 119 of 125, so one Batch came back as unusable output and `batch_extract` returned `{}` as designed; the three later runs extracted all 125. The script does not say which Batch failed.

- **Merge prompt over-merged.** With the LLD's wording, the cap of 300 names gave 79 merges, many wrong: `t sql` and `pl sql` into `sql`, `aws` into `aws cloud services`, `flight dynamics` and `statics` into one, `llms` into `generative pretrained transformers gpts`, `engineer in training eit` into `fundamentals of engineering fe`. The earlier probe (166 names, 12 merges) did not show this. This run sent a longer list and a wider fixture set (including USAJOBS engineering Postings); which of those, or model variance, caused it was not isolated.
- **Prompt change** (`MERGE_SYSTEM` in `analysis/prompts.py`): added "Most names belong to no group, so expect only a handful of groups" and named three failing shapes ("pl sql" and "sql", "flight dynamics" and "statics", "aws" and "aws cloud services") as not spellings of each other. The next run gave 17 merges, mostly correct (`airflow`, `spark`, `azure`, `glue`, `etl`, `nlp`). This is one run per wording, so the improvement is a direction, not a measured rate.
- **Assertions pass** on the last run after the change (the output of the first post-change run was not read): `AWS` and `S3` stay apart, `Git` and `GitLab` stay apart (both pairs appear in this Sample; on the first run `Git` and `GitLab` did not both appear, so that check was skipped).
- **Employer types** came out at about 50% direct and 49% agency, with 2 Postings of unknown type. Not checked against the individual employers here.
- **Remaining weak spots** (not fixed here): `spark pyspark → pyspark` still gets through; and a pair can be grouped in both directions in one answer (`data analytics → analytics` and `analytics → data analytics`), which maps each to the other and leaves two keys instead of one. That only splits a count, never inflates it, but a canonical-closing step in `_aliases` would fix it if the run shows it often.
- **Step 11** (is an `unknown` pay period on advertised Adzuna pay annual) is still unproven: the fixtures have only estimated pay, so it needs the first live Run.
