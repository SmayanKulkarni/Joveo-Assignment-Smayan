# 03: The clarify loop, re-ask cap and settling

**What to build:** "Engineer, Texas" pauses with one targeted question per flagged field, the answer goes back to `intake` for a new draft, and the Run carries on. A field asked twice settles with an Assumption or aborts the Run, with the reason visible in `scout show`. `plan` stays a stub. Spec: [Request & Plan LLD](../../../docs/lld/request-plan.md) §4, §5 (`clarity_check` steps 3-5, settling, `clarify`), §12 pass 1 steps 4, 5 and 7.

**Blocked by:** 02: A clear request reaches `plan`.

**Status:** done

- [x] A flagged field is asked while it has fewer than 2 earlier questions with the same `about`, and settled at 2
- [x] The cheap tier drafts one private `QuestionDraft(text, options)` per field, with at most 4 options, and code sets `about` and `answer=None`
- [x] A question about an unsupported country lists the supported ones, from code
- [x] `clarify` pauses with only the unanswered questions and matches answers by position: missing answers become blank, extras are dropped, and a blank counts as vague
- [x] `clarify` returns to `intake`, and `runtime/graph.py` has the new edge
- [x] Assumptions are written only when `clarity_check` finishes, so a field settled and later cleared leaves none
- [x] An abort writes no `hiring_request`, logs a `route` entry with the reason and goes to END
- [x] Test: only flagged fields are asked, and a third ask settles instead
- [x] Test: each row of the settling table: a vague value is kept with an Assumption and no LLM call, a null `location` or `country` uses `default_country` with an Assumption, an unsupported `country` aborts, and a null `role` aborts
- [x] Test in a one-node graph with a checkpointer: padding, extras dropped, and a `Command(resume=ClarifyAnswer(...))` round trip
- [x] Graph test with other stages stubbed: "Engineer, Texas" goes through a real `clarify` loop to `fetch_agent`

**Notes:** the unsupported-country question takes its options from `sorted(ADZUNA_CURRENCY)`, so the user sees country codes. A field settles as a country-wide search on `default_country`, replacing a non-null `location` too, as the LLD table reads.
