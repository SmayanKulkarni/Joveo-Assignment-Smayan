# 03: Guardrails on Postings

**What to build:** A Posting whose text addresses an AI is dropped from the Run with a Caveat, a sentence can't pass as a skill, and an unsafe Posting URL never becomes a link. [Guardrails for the existing LLM nodes](../../resume-accounts-sources/final-decisions.md#guardrails-for-the-existing-llm-nodes) is the spec.

Before starting, check the open question at the top of [Final decisions](../../resume-accounts-sources/final-decisions.md#check-these-first): Jev may not meet the destination's "open-weight" wording. Unless the user has changed that call, build with Jev.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] An `addressed_to_ai` Noul travels in the existing `relevance` request, adding no requests
- [x] A hit at `p_yes` of at least 0.7 (a constant with the other thresholds) drops the Posting from the Sample, records its key in `guard_flags`, and logs "N Postings removed: their text addressed an AI"
- [x] Flagged titles are left out of the rejected titles sent to `broaden`
- [x] Extraction drops skill names over 40 characters or 4 words
- [x] Only `http` and `https` Posting URLs become links, on screen and in downloads
- [x] `fake_classifier` knows the new Noul and defaults to not flagged, and `relevance` replay entries are re-recorded
- [x] Fixtures prove each rail: the 40 injected Postings and 5 benign attack-quoting adverts from the research, a sentence as a skill, and a `javascript:` URL
- [x] One live check on the fixtures confirms the 0.7 cut still separates them

## Built

- Jev was used, as the ticket's default says.
- Rail 3 was already in place (`clients/web.py` `_http_url` and `brief/markdown.py` `_link`), with `javascript:` tests in `test_web_api.py` and `test_brief_render.py`, so no code changed for it.
- No recorded replay files are committed, so nothing was re-recorded. Any local `REPLAY_CACHE` misses on `relevance` and records it again.
- Fixtures are `tests/fixtures/jobs/guard_postings.json`: 40 injected Postings built from the recorded Adzuna and USAJOBS ones, and 5 benign adverts I wrote, one of which quotes attacks.
- **Live check, 2026-11-02:** the first Noul wording scored my "Customer Service Agent" advert (it tells its employee to answer every question and ignore some requests) at 0.73, above the cut. I added "anything addressed to the job seeker or the person who will hold the job" to the wording. Then all 40 injected Postings scored 0.90 to 0.99 and the benign ones 0.03 to 0.45, so 0.7 separates them. The sample is small and the benign adverts are mine.
