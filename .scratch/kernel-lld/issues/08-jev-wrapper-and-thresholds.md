# Jev wrapper and thresholds

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 03, 04

## Question

What is the Kernel's Jev wrapper: interface, threshold config, fallbacks, tracing and tuning?

- **Interface** for the three placements (clarity check, Posting relevance, critic): what a stage passes (criteria/labels, text) and what it gets back (outcome, probability/distribution, threshold applied, reason for `run_log`).
- **Threshold config**: shape keyed by model and placement; where it lives; first-cut values; the "uncertain" band and what it routes to.
- **Tuning procedure**: how thresholds get calibrated per model (labelled examples, optionally a LangSmith dataset), given final values are out of scope for this map.
- **Fallback chain**: OpenRouter `systemone` → decisions endpoint → direct TypeSafe → LLM structured output (loses distributions; how thresholds apply then).
- **32 KB guard**: truncate, split, or refuse oversized input.
- **Batching/concurrency** for N relevance calls per Run.
- **Tracing**: `@traceable` (if needed) with criteria, probabilities, threshold, outcome, cost and request id.
- **Test seam**: a fake classifier for tests and replay.

Input from [Live smoke test: OpenRouter LLM, Jev and LangSmith](04-live-smoke-test-openrouter-jev-langsmith.md): LangSmith already traces and prices Jev (`llm` run, cost matches OpenRouter exactly), so no `@traceable` and no custom price. The OpenRouter id and cost still need the HTTP hook if the `run_log` wants them. Easy inputs return saturated probabilities, so tuning needs hard examples.

## Answer (2026-10-30)

Grilled with the user. The Kernel's Jev wrapper is a thin class over one long-lived `TypeSafeClassifier` (`langchain-typesafe==0.0.1a3`, `model="typesafe/jev-1.14"`, OpenRouter `base_url` and key).

- **Interface**: Noul only, since all three placements are yes/no questions. Choice and Score get added when a stage needs one. `Placement = Literal["clarity", "relevance", "critic"]`. One method, `await jev.judge(placement, state: dict, questions: dict[str, Noul]) -> dict[str, Judgement]`. Several questions share one request (e.g. clarity asks about role, location and seniority together). `Judgement` holds `outcome: bool`, `p_yes`, `cut`, `model`, `source` (`"jev"` or `"llm_fallback"`), `truncated` and a one-line `reason` for `run_log`. Stages own the question text and phrase it so that "yes" is the side that has to clear the bar.
- **Thresholds**: a single cut per `(model, placement)`, `outcome = p_yes >= cut`, with **no uncertain band**. No Pause exists to route "uncertain" to, and collapsing it to one side is the same as a single cut. `p_yes` and `cut` are logged so tuning can see close calls. Cuts live in a dict literal in `kernel/thresholds.py`: no loader, no env overrides. **Every first-cut value is 0.5**, marked untuned until the sweep runs, and that includes the `llm:cheap` key, where the cut doesn't matter because p is always 0 or 1.
- **Picking the cut**: the cut comes from `response.model` by the longest config key that is a prefix of it, since Jev returns a dated snapshot like `typesafe/jev-1.14-20261014`. `source` comes from the same match. If no key matches, it fails loudly, so a new Jev version never runs on stale cuts. At construction, the wrapper checks that every placement has a cut for each model in its chain.
- **Fallback chain**: `jev-1.14` with `with_retry` (3 attempts, backoff, on 429, 5xx, connection errors and timeouts), then `with_fallbacks` to an LLM adapter on the tier factory's **cheap** tier, triggered by exhausted retries, a malformed 200 or a 404, with an explicit `exceptions_to_handle`. The adapter sends the same state and Noul text and gets back `{id: {answer: bool, reason: str}}` via structured output. It maps that to `p_yes` 0 or 1 and builds a `ClassifierResponse` with `model="llm:cheap"`, so the routers don't change. It asks for no verbalised probability, because that would be uncalibrated noise. It **never** falls back on 400 or 422 (our bug) or on 402 (the LLM is on the same OpenRouter account). Those exceptions, and any raised after the chain runs out, propagate unchanged. Dropped: the `/api/alpha/decisions` endpoint (same failure modes as `/v1/systemone`) and direct TypeSafe (no key). Adding `jev-1.13` as a middle hop waits until 1.14 proves flaky, since it would need its own cuts.
- **32 KB guard**: measure `len(json.dumps(state, ensure_ascii=False, separators=(",",":")).encode())` against a 30,000-byte budget. If it's over, cut the longest string value, ending it with `…[truncated]`, until it fits, and set `truncated=True`. Never raise. Stages may pre-trim more cleverly.
- **Concurrency**: one `asyncio.Semaphore` in the wrapper, size 8 from settings. It bounds every Jev call in the process, across placements and concurrent Runs. Relevance just `asyncio.gather`s `judge` calls.
- **Tracing**: no `@traceable` and no injected `httpx2` client or response hook. LangSmith already traces and prices Jev, and keeping the classifier's own client keeps its 30 s timeout, which sidesteps the 5 s injected-client trap. Each call passes `config={"run_name": f"jev:{placement}", "tags": ["jev", placement], "metadata": {"cut": ..., "model": ...}}`. The OpenRouter generation id and cost stay out of `run_log`; add the hook if per-call ids are ever needed.
- **Test seam**: constructor injection, `Jev(classifier: Runnable[ClassifierRequest, ClassifierResponse], cuts)`. `make_jev(settings)` builds the production chain. A `fake_classifier({"q_id": 0.9, ...})` helper in the Kernel's test utilities returns canned `ClassifierResponse`s.
- **Tuning procedure**: per placement, 20–40 *hard* labelled examples in `evals/jev/<placement>.jsonl` (easy inputs saturate at 1.0/0.0). A script runs them through the real `Jev`, sweeps the cut from 0.05 to 0.95 and prints precision, recall and F1 per cut. Relevance optimises for precision and clarity for recall of "ambiguous". A human then edits `thresholds.py`. Re-run whenever the model id changes. A LangSmith dataset is optional.
