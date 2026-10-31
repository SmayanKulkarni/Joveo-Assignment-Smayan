# 06: The LLM writer

**What to build:** a Run with Postings now gets its Summary and Insights from the strong Tier, checked in code so that it can't cite an unknown Stat or invent a figure, and falling back to the rule-written draft rather than ending without a Brief. Spec: [Brief LLD](../../../docs/lld/brief.md) §5, §11 (weak Samples), §13, §14, §15 pass 1 steps 5 and 6.

**Blocked by:** 03: A rule-written Brief with tagged, traceable Insights, and 04: Hiring Outlook

**Status:** done

- [x] The check rejects, and so retries with feedback: an unknown Stat id, a blank Summary or Insight, one with no Stat ids, no Insights, over the cap, and a figure in no Stat, Caveat or the request
- [x] Figure edge cases pass as in §5: `S3` isn't a number, `$134k` is checked as 134,000, 38% passes on 38.4%, and a figure from an uncited Stat passes
- [x] `rule_draft` passes its own checks
- [x] A bad reply passes on the feedback retry
- [x] Bad output from every model, including a runaway, gives `rule_draft`, the "Brief written by rule" Caveat and `revisions` at the cap
- [x] A transient failure on every model propagates, so `scout resume` reruns only this node
- [x] The stored draft is a plain `BriefDraft`, not the local checked subclass, and survives a checkpoint
- [x] `WRITE_SYSTEM` follows §14, with input in its fixed order and values formatted, and Posting text and keys are never sent
- [x] The cap is `MAX_INSIGHTS`, or `THIN_MAX_INSIGHTS` under `THIN_SAMPLE`
