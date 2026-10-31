# 07: Brief live smoke

**What to build:** a script runs fixture Postings through Analysis and the real writer and prints the Brief, which proves the stage on real model output and gives the write-up its "what changed after testing". It spends no job API calls. Spec: [Brief LLD](../../../docs/lld/brief.md) §14, §15 pass 1 step 9.

**Blocked by:** 05: Client Recommendations, and 06: The LLM writer

**Status:** done

- [x] `scripts/smoke_brief.py` (not in CI) runs `tests/fixtures/jobs/` through Analysis then the writer on `minimax/minimax-m3.1-flash`
- [x] It prints the Brief, the Outlook and how often the checks retried
- [x] It's run 5 times, and results and any change to the prompts are recorded in this ticket for the write-up

## Results (2026-10-31, `minimax/minimax-m3.1-flash` for both Analysis and the writer, 125 fixture Postings)

Two sets of 5 runs of `scripts/smoke_brief.py`. The second set also printed each reply's finish reason.

| Set | Written by the model | Checks retried | Written by rule |
|---|---|---|---|
| 1 | 4 of 5 | not counted | 1, after a single model call, so a reply cut off at `WRITE_MAX_TOKENS` |
| 2 | 5 of 5, each with 8 Insights | 1 of 5, passing on the feedback retry | 0 |

- Every Brief had a Competitive Outlook (61 employers, a median of 2 to 4 years asked, 23 to 26% senior), a Data Engineer title, an estimated pay band of 117,761 to 184,620 USD/year and 5 top skills.
- Output tokens ranged from about 600 to 2,300 for the same input, so the reasoning share varies, and 4,096 left little room on a bad draw. One run of ten ended on the rule draft this way, which is the designed fallback. Raise `WRITE_MAX_TOKENS` if it recurs on the two-model chain.
- One run in the second set needed the feedback retry and then passed. Its cause wasn't recorded.
- In the one Brief read in full, estimated pay was labelled as Adzuna's estimate and snippet limits were mentioned for skills.
- No prompt changes were made after testing.
