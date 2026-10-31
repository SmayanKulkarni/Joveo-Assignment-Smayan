# 01: Postings become grounded Extractions

**What to build:** a Sample fans out into Batches through `Send`, the cheap tier extracts them, and code drops any skill or year that isn't in the Posting's text, so `extractions` holds only grounded facts. A transient failure stops the Run and `resume` reruns only the failed Batch, while bad output skips that Batch. `normalise_skills` and `stats` stay stubs here. Spec: [Analysis LLD](../../../docs/lld/analysis.md) §2, §3, §4, §5, §6, §11, §13 steps 1-4 and the resume half of step 9.

**Blocked by:** None (can start immediately). Collection pass 1 is done, so `sample`, `fetches` and `"analyse"` exist.

**Status:** done

Kernel and Runtime changes:

- [x] `LLMExhausted.bad_output` is set from whether the last failure was bad output
- [x] `State` gains `skill_aliases`, owned by Analysis, defaulting to empty
- [x] `ExtractBatch` is in `ALLOWED_MSGPACK`
- [x] `normalise_skills` is in `EDGES` and `OWNERS` with a stub node, and runs between `batch_extract` and `stats`
- [x] `analysis.fan_out` replaces `stub_fan_out`
- [x] `analysis/types.py` holds the §3 types, every LLM field required with no defaults
- [x] Test: `Extraction` and `ExtractBatch` survive the Runtime serde test under strict msgpack
- [x] Test: `bad_output` is right for each kind of failure

`_batches` and `fan_out`:

- [x] Batches hold at most 20 Postings or 20,000 description characters, sorted by key
- [x] An empty Sample routes to `"stats"`, otherwise one `Send` per Batch
- [x] Test: 45 Batches for 900 Adzuna-sized Postings
- [x] Test: the count limit, the character limit with USAJOBS-sized text, and one oversized Posting
- [x] Test: the same order whatever the input order

Grounding:

- [x] A skill whose folded name isn't a whole-word match in the folded title and description is dropped and counted in `ungrounded`
- [x] A `years_min` over 40, or whose number isn't in the text, becomes null
- [x] Test: `C` isn't grounded by `C++`, and `R` isn't found inside a word
- [x] Test: an invented skill is counted in `ungrounded`
- [x] Test: `years_min` of 5 passes on "5+ years", fails when absent and fails at 41

`batch_extract`:

- [x] Uses `tiers.structured("cheap", BatchFacts, system=EXTRACT_SYSTEM, name="batch_extract", max_tokens=EXTRACT_MAX_TOKENS)`
- [x] The input is one §6 block per Posting, with `ref` as its position, and no Hiring Request
- [x] `EXTRACT_SYSTEM` in `prompts.py` follows every §11 rule, starting from the probed wording in the Prompts design ticket
- [x] The branch writes only `extractions` and never logs
- [x] Test with fake chains: refs map to the right keys, and a repeat and an out-of-range ref are ignored
- [x] Test: bad output returns `{}`, and a transient `LLMExhausted` raises

Resume:

- [x] Test with a checkpointer and other stages stubbed: one Batch raising transiently stops the Run, `resume` reruns only that Batch, and `normalise_skills` runs once
