# 09: The real critic and revisions

**What to build:** Jev judges each Insight against its cited Stats, flagged Insights get rewritten up to twice without touching the accurate ones, and whatever stays unconfirmed ships capped at Medium with a Caveat saying so. Spec: [Brief LLD](../../../docs/lld/brief.md) §5 (`_revise`), §6, §10, §13, §14, §15 pass 5.

**Blocked by:** 07: Brief live smoke

**Status:** done

- [x] Only fresh Insights are judged, and the Summary, Outlook and Recommendations never are
- [x] Kept Insights stay byte-identical across a revision, and `critic_verdicts` stays aligned with the start of `brief_draft.insights`
- [x] A reply with no replacements drops those claims
- [x] `after_critic` goes to `render` when all are supported or at `MAX_REVISIONS`, and otherwise back to `write_brief`
- [x] Bad output during a revision stops the loop with the draft standing, and a transient failure propagates
- [x] An unsupported Insight ships capped at Medium, with the "Insights not confirmed" Caveat logged before Run Notes are built
- [x] The "Critic degraded" Caveat fires once per pass with its count, on any `llm_fallback` or `truncated` Judgement
- [x] `critic` logs a `route` entry with each Insight's score and the outcome
- [x] `REVISE_SYSTEM` and `CRITIC_NOUL` follow §14, tested with `fake_classifier`
- [x] The smoke adds `critic` on `typesafe/jev-1.14` and prints each score, and results are recorded in this ticket for the write-up

## Results for the write-up

Two live runs of `scripts/smoke_brief.py` on the fixture (125 Postings, writer `minimax/minimax-m3.1-flash`, critic `typesafe/jev-1.14`):

| Run | Writer calls | Scores (cut 0.5) | Flagged | After revision |
|---|---|---|---|---|
| 1 | 3 (2 retried) | 0.75 0.97 0.98 0.98 0.95 **0.34** 0.98 0.99 | 1 of 8 | replacement scored 0.96, none unsupported |
| 2 | 1 | 0.98 0.98 **0.17** 0.91 0.95 0.98 0.92 0.78 | 1 of 8 | replacement scored 0.98, none unsupported |

- Run 2's flagged Insight was a real fault: "Staffing agencies place 53 of 125 postings, ahead of direct employers at 64". It ranked a smaller figure above a larger one.
- Both runs ended after one revision with the kept Insights untouched and no Caveat.
- Nothing needed tuning in `CRITIC_NOUL` or `REVISE_SYSTEM` after these runs.
