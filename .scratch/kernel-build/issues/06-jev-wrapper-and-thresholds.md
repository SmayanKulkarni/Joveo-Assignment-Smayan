# 06: Jev wrapper and thresholds

**What to build:** a stage asks Jev yes/no questions for a placement and gets back `Judgement`s with an outcome, probability and cut, from the real `typesafe/jev-1.14` through OpenRouter. Oversized input is truncated rather than rejected, and a Jev model with no configured cut fails loudly. Spec: [Kernel LLD](../../../docs/lld/kernel.md) §11, §15, §16 steps 5 and 7.

The LLM fallback hop is ticket 07. Here, exhausted retries propagate, so this ticket doesn't depend on the LLM tier factory. Add the Jev call to the live smoke script, creating the script if ticket 04 hasn't landed.

The tuning sweep (`evals/jev`) is not built here: it is in neither build pass, and all cuts ship at 0.5 marked untuned ([future scope](../../../docs/lld/future-scope.md)).

**Blocked by:** 01: Project skeleton and settings.

**Status:** done

- [x] `Jev(classifier, cuts)` takes an injected classifier, and `make_jev(settings)` builds the real one with OpenRouter's `base_url` and key
- [x] `judge(placement, state, questions)` returns a `Judgement` per question, with `outcome = p_yes >= cut`
- [x] `fake_classifier({...})` returns canned answers
- [x] Test: the cut comes from the longest config key that prefixes the returned model id, so a dated snapshot resolves
- [x] Test: an unknown model fails loudly
- [x] Test: construction fails when a placement has no cut for a model in the chain
- [x] Test: state over 30,000 bytes has its longest string truncated with the marker until it fits, `truncated=True` is set, and nothing raises
- [x] Test: concurrent calls never exceed the process-wide semaphore
- [x] Test: 429, 5xx, connection errors and timeouts are retried; 400 and 422 are not
- [x] Each call passes `run_name=jev:<placement>`, tags, and the cut and model as metadata
- [x] Live smoke: one Noul call returns a `Judgement` with a dated model id and shows in LangSmith
