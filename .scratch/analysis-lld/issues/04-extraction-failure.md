# When extraction fails

Type: grilling (delegated to the agent)
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01

## Question

A Batch can fail because the provider is down, or because the model keeps returning output that won't validate. What happens to the Run in each case? The spec says neither a crash nor garbage is acceptable.

## Answer

The two need opposite handling, so `LLMExhausted` gains `bad_output: bool`, true when the last error in the chain was bad output.

| Failure | What happens | Why |
|---|---|---|
| Transient, every model (`bad_output` false) | Propagates. The Run stops at `batch_extract`, and `scout resume` reruns only that Batch | Waiting fixes it. A Brief built without those Postings would be worse than a stopped Run, and the probe confirmed finished Batches aren't repeated |
| Bad output, every model (`bad_output` true) | The Batch returns `{}` and its Postings have no Extraction | The same text would fail the same way on every resume, so propagating would trap the Run forever |
| A Posting left out of a good response | No Extraction for it | Too rare for a retry path |
| `normalise_skills` bad output | Skills stay merged by folding alone, with a Caveat | Same reasoning, and folding alone still gives true counts, only more split |

**No new state.** The missing Postings are `set(sample) - set(extractions)`, so `stats` raises the one Caveat. Nothing has to be recorded by a branch, which couldn't log anyway.

**`stats` never fails on this.** Skills, seniority and agency Stats use the Postings that were extracted, and their labels say so ("of 118 extracted"). Pay, demand, employers and titles need no Extraction at all, so even a fully failed extraction yields a usable, Caveated Brief.

**No splitting a bad Batch in half to retry.** It's the only way to recover those Postings, but bad output hasn't been seen at 8,192 tokens, so it would be code for a case with no evidence. It's listed in `future-scope.md` with what would bring it back.
