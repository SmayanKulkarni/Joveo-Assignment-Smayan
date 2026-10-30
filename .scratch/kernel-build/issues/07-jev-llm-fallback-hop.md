# 07: Jev LLM fallback hop (pass 2)

**What to build:** when Jev is down, a Run keeps going on the cheap LLM tier instead of stopping. Routers don't change, because the fallback still yields a `Judgement`, marked as made without Jev's probabilities so the calling stage can log a Caveat. Spec: [Kernel LLD](../../../docs/lld/kernel.md) §9, §11.

Pass 2: not needed for the walking skeleton. Raising the Caveat is each stage's job, not this ticket's.

**Blocked by:** 04: Tiers.structured, end to end; 06: Jev wrapper and thresholds.

**Status:** done

- [x] `make_jev` chains `jev-1.14` with retry, then falls back to an adapter on `tiers.structured("cheap", ...)` with an explicit exception list
- [x] The adapter sends the same state and question text and gets `{id: {answer, reason}}` back
- [x] Answers map to `p_yes` of 0 or 1 with model `llm:cheap`, and `source="llm_fallback"` on the `Judgement`
- [x] Test: exhausted retries, a malformed 200 and a 404 reach the adapter
- [x] Test: 400, 422 and 402 propagate without touching the LLM
- [x] Test: a failure after the adapter also runs out propagates unchanged
- [x] Test: the existing cut lookup resolves `llm:cheap`
