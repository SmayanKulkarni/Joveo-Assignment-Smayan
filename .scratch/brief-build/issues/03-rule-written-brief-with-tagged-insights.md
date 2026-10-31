# 03: A rule-written Brief with tagged, traceable Insights

**What to build:** a Run with Postings ends in a real Brief with no LLM writing it. Insights come from Stat labels, each carries a Confidence Tag with its reason, and every number reaches a real ad in two steps. This `rule_draft` path is the fallback the writer in ticket 06 relies on. Spec: [Brief LLD](../../../docs/lld/brief.md) §5 (`rule_draft`), §6, §9 (coverage), §11, §12, §15 pass 1 steps 2 and 7, and the fixture table in [Confidence Tag rules](../../brief-lld/issues/03-confidence-tag-rules.md).

**Blocked by:** 02: A zero-Posting Run produces a real Brief

**Status:** done

- [x] A Run with Postings reaches `done`, with `rule_draft` as its draft for now and the Caveat from §13 left to ticket 06
- [x] Each Stat rates by the §6 table, an Insight takes its weakest cited Stat, and `competition.employer.*` is exempt from the employer minimum
- [x] Each of the four Medium caps works: estimated pay, skills from snippets when any Adzuna Posting is in the Sample, old data, and an unsupported verdict at the cap (a missing verdict doesn't cap)
- [x] The fixture table in the Confidence Tag ticket passes, and `confidence_reason` states the weakest Stat and any cap
- [x] `_fill_gaps` adds one Stat-label Insight per uncovered Dimension at `THIN_SAMPLE` or more, or when no Insight survived, after the writer's Insights
- [x] Evidence is the union of the cited Stats' Postings, and an Insight's `dimension` is its first cited Stat's
- [x] The Markdown shows tagged Insights with their reasons and the key, `E` references by first appearance with identical Postings sharing one, the Evidence list, the Postings table, and the Weak Sample line under target
- [x] Posting text can't break the output: `|` and newlines are stripped from cells, and a non-http link is left out
