# Writer failures and bad citations

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01, 02

## Question

What happens when the draft cites a Stat id that doesn't exist, states a figure in prose that no cited Stat holds, or leaves a required part empty? Which of those are retried with the error fed back, dropped, or raised as a Caveat? What happens on transient failure, and on bad output from every model, given that a Run should never end without a Brief or return garbage?

## Answer

Decided by the agent, on the user's instruction.

**A per-Run validator makes Kernel's feedback retry do the work.** `checked_draft(...)` returns a `BriefDraft` subclass with a `model_validator` that closes over this Run's Stats. `Tiers.structured` feeds its errors back with no new retry code. The node then copies the result into a plain `BriefDraft`, because a checkpoint stores the class path and a local class can't rehydrate. The limits stay out of the JSON schema, which keeps it the same across Runs.

| Fault | Result |
|---|---|
| Unknown Stat id | Retried |
| Summary or Insight with no Stat ids, or blank | Retried |
| No Insights, or over the cap | Retried |
| A figure in no Stat, Caveat or the request | Retried |
| A figure from a Stat it didn't cite | Passes here. The critic flags it |
| A Dimension with no Insight | Not checked here. `render` fills it ([What focus changes in the Brief](06-what-focus-changes.md)) |
| Transient on every model | Propagates. The Run stops, and `scout resume` reruns only this node (Kernel §12) |
| Bad output on every model, including a runaway | The rule-written draft below, with a Caveat |

**The figure check is deliberately loose.** Tied to cited Stats, it exhausted a thin run, while [Live check of the draft design](13-live-check-of-the-draft-design.md) got 8 of 8 valid with any Stat, and every figure the check rejects is one the Sample doesn't contain. So it catches inventions, and the critic catches wrong attribution.

- Numbers are read with `(?<![\w.])\d[\d,]*(?:\.\d+)?[kKmM]?(?!\w)`, so `S3` isn't a number, and `$134k` is 134,000.
- A number also passes as a whole-number rounding of an allowed one, so 38% matches 38.4%.
- Number words like "five" aren't caught. The critic is the only check on them.

**Never end without a Brief, and never return garbage.** The rule-written draft is plain code: a Summary giving the Sample size and one Insight per Dimension with Stats, reusing the fill in `render`, so its figures are all true. Bad output would repeat on every resume, as in Analysis's Batch rule. It raises the Caveat "Brief written by rule: every model's draft failed its checks, so Insights state computed figures directly" and sets `revisions` to the cap, so no further LLM call is spent.

**Salvaging the valid Insights from a failed draft was rejected,** since `LLMExhausted` doesn't carry the output and adding that isn't worth a rare path.

**Runaway.** The live check saw one at 125 Postings, so `WRITE_MAX_TOKENS = 4096` limits its cost. The largest reply the first probe saw was 2,476 tokens, and that was on a bigger schema. `finish_reason=length` already moves to the next model with no retry (Kernel §12).
