# The critic

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01, 02, 08

## Question

What exactly is Jev asked per Insight, with what input and threshold, and does it also check recommendations? What does `write_brief` get back on a revision, what is the revision cap, which fields reset and which decide the route? What ships when the cap is hit with an Insight still unsupported? Keep this small enough that the build can skip the critic without reopening anything.

## Answer

Decided by the agent, on the user's instruction.

**What's judged:** each Insight, one Jev request each, gathered at once. Not:
- **Recommendations and the Outlook,** which code builds from Stats.
- **The Summary,** which scored 0.14 and 0.15 even when accurate, so would force every Run to the cap. The figure check covers its numbers, and it stays short by prompt. That it isn't judged belongs in the write-up.
- **Insights added by `render`,** which are Stat labels as written.

**The state,** per [Live check of the draft design](13-live-check-of-the-draft-design.md), is `hiring_request`, the Caveat messages, `claim` and `stats` (`id`, `label`, `value`, `unit` of each cited Stat). No Postings: the first probe showed they change nothing and lower scores. That narrows HLD §6's "the Postings it cites", and the requests stay under 2 KB, so Jev's limit never comes up.

**The question** says yes if each figure and comparison in the claim matches the cited Stats, the request or the Caveats, and that fair descriptive wording and stating only some figures are fine. No if a figure is wrong, a comparison or ranking isn't shown by the cited Stats, or estimated pay is presented as advertised. The cut stays at the existing 0.5, untuned.

**Three `State` fields, all owned by Brief:**

| Field | Written by | On a revision |
|---|---|---|
| `brief_draft: BriefDraft \| None` | `write_brief` | Replaced with kept Insights first, then replacements |
| `critic_verdicts: list[InsightVerdict]` | `critic` appends. `write_brief` cuts it to the kept ones | Matches the start of `brief_draft.insights`, by position |
| `revisions: int` | `write_brief` | Goes up by one |

`InsightVerdict` is `supported: bool` and `p_yes: float`. A short list means the rest haven't been judged, so `critic` judges only `insights[len(critic_verdicts):]`.

**A revision replaces only flagged Insights.** The Summary and passed Insights stay as they are. The input lists the flagged ones with what they cited, and the writer returns `BriefRevision`, with `insights` as replacements and none for a claim it can't support. A whole-draft revision rewrote accurate Insights and their scores fell, while this fixed 2 of 3. No reason comes back, because Jev gives none: only `llm_fallback` does.

**The cap is `MAX_REVISIONS = 2`.** `after_critic` is pure: `render` if every verdict is supported or `revisions >= MAX_REVISIONS`, otherwise `write_brief`.

**Bad output during a revision** keeps the current draft and sets `revisions` to the cap, so the Run moves on with what it has. Transient failure propagates, as elsewhere.

**What ships at the cap:** the Insight, unconfirmed.
- **Its tag is capped at Medium,** with `confidence_reason` saying "the critic could not confirm it". The spec defines Medium as "share with a caveat". This adds a fourth cap to [Confidence Tag rules](03-confidence-tag-rules.md).
- **`render` raises one Caveat,** "Insights not confirmed", with the count.
- **Dropped was rejected.** The cut is untuned and the first probe's accurate claims scored low. Low was rejected for the same reason: figures already passed the check, so Low would misstate them.

**Other Caveats:** any `llm_fallback` or `truncated` Judgement logs "Critic degraded" once per pass, with the count (Kernel §11).

**The build can skip it.** Until pass 5, `critic` is a pass-through stub. `critic_verdicts` stays empty, so `after_critic` goes to `render`, nothing is capped, and nothing else changes.
