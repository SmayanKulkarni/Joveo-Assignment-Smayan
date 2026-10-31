# Batching and fan_out

Type: grilling (delegated to the agent)
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01

## Question

How is the Sample split into Batches, what does a `Send` carry, and how does zero Postings reach `stats`? The Sample has no cap, so 3 Attempts can bring up to 900 Postings.

## Answer

**`MAX_BATCH_POSTINGS = 20`, `MAX_BATCH_CHARS = 20_000`, `max_tokens = 8192`.**

- 20 Postings used 4,092 of 8,192 output tokens in the probe, which leaves room for a heavier reasoning turn. 40 used 6,199, with five times the rate of skills not in the cited Posting.
- A smaller Batch also loses less when one is skipped, and a rerun repeats less.
- The character cap is what handles USAJOBS: 20,000 characters is about 5 of its 4,000-character descriptions, and about 40 Adzuna snippets, so for Adzuna the count limit applies first. Well within the context window either way, which is the spec's edge case.
- 900 Postings is 45 Batches. At 15 s each and the existing `llm_concurrency` of 20, that's under a minute.
- The 60 s call timeout holds at this size.

**Greedy packing over Postings sorted by key,** so the same Sample always gives byte-identical prompts, which the replay cache needs. A single oversized Posting still gets its own Batch.

**`ExtractBatch(postings: list[Posting])` is the payload,** because `owned()` requires a `Send` arg to be a model. It carries no Hiring Request: extraction doesn't depend on the request, which also lets identical Batches hit the replay cache across Runs.

**Refs are positions in the Batch (0, 1, 2…),** not Posting keys. They cost fewer tokens, and the model can't return a key that looks real but isn't. A `ref` outside the Batch is ignored, the first answer wins on a repeat, and a Posting with no answer simply has no Extraction ([When extraction fails](04-extraction-failure.md)).

**`fan_out(state)`** returns `"stats"` when the Sample is empty, otherwise one `Send` per Batch. A zero-branch fan-out would stall the Run (HLD §4).

**`Send` from pass 1, reversing HLD §11's "sequential extraction" then "Send fan-out" split.** The two differ by a few lines, and building sequential first means writing the failure and progress paths twice, days before the deadline.
