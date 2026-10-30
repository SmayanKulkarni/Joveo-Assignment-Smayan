# 02: A clear request reaches `plan`

**What to build:** "Data Analyst, Bangalore" goes through the real `intake` and `clarity_check` with no question asked, and the final `hiring_request` is set for the next stage. `plan` stays a stub. Fields that need asking are flagged and routed, but drafting questions and settling at the cap belong to ticket 03. Spec: [Request & Plan LLD](../../../docs/lld/request-plan.md) §4, §5 (`intake`, `clarity_check` steps 1-2 and 5), §7, §9, §12 pass 1 steps 3-4 and part of 7.

**Blocked by:** 01: Kernel contract and Request & Plan types.

**Status:** done

- [x] `request_plan/prompts.py` and `request_plan/nodes.py` exist, with `make_nodes(deps)` and `ROUTERS`, and the prompts follow the rules in §7
- [x] `intake` uses the cheap tier, writes `request_draft` and one `note`, and is safe to rerun
- [x] Code flags a null `role`, `location` or `country`, or a `country` outside `ADZUNA_CURRENCY`, with no Jev call
- [x] One Jev request judges each field that exists and isn't already flagged: `role`, `location`, and `seniority` only if the user gave one. "Yes" means too ambiguous, and no call is made if no field qualifies
- [x] A missing `seniority` is not ambiguous
- [x] `clarity_check` alone writes `hiring_request`, and logs a `route` entry with each field's outcome and reason
- [x] A `Judgement` with `source="llm_fallback"` or `truncated=True` logs a Caveat
- [x] `after_clarity` reads only state, and `runtime/graph.py` has the new `clarity_check` targets
- [x] Test with fake chains: `intake` writes the draft, and answered questions reach the prompt
- [x] Test with `fake_classifier`: a clear request gets no question and sets `hiring_request`, a missing field skips Jev, and a fallback `Judgement` logs a Caveat
- [x] Test: all `after_clarity` outcomes

**Notes:** `build_graph` wires the real stage unless `Deps.stub_stages` is set, which `fake_deps` does, so the Runtime stub tests are unchanged. A country problem is flagged against `location`, since `country` is not a `RequestField`. `nodes.py` holds tickets 02-04 and 06 together.
