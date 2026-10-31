# 05: Analysis live smoke

**What to build:** a script runs fixture Postings through the real model and prints what Analysis made of them, which proves the whole stage and shows any bad merge. It spends no job API calls. Spec: [Analysis LLD](../../../docs/lld/analysis.md) §7, §11, §13 step 10.

**Blocked by:** 02: Skill spellings merge into canonical names, 03: Demand, skills, competition and title Stats, and 04: Pay Stats.

**Status:** ready-for-agent

- [ ] `scripts/smoke_analysis.py` (not in CI) runs fixture Postings through `minimax/minimax-m3.1-flash`
- [ ] It prints the top skills, every merge and the employer types
- [ ] It asserts that `AWS` and `S3`, and `Git` and `GitLab`, stay apart when both appear
- [ ] Results and any change to the prompts are recorded in this ticket for the write-up
