# Clarity check and the re-ask cap

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01

## Question

What does `clarity_check` judge, how are questions chosen, and what happens when a field is still unclear after the one re-ask the HLD allows?

- Which Jev questions it sends, and which side is "yes".
- How the spec's 1–3 question limit is met, and how a clear request skips the Pause.
- What happens at the cap for a vague value, a missing location, an unsupported country and an unreadable role.

## Answer

Decided by grilling.

- **Code flags what is plainly missing,** with no Jev call: `role` null, `location` null, `country` null, or `country` outside `ADZUNA_CURRENCY`.
- **Jev judges the rest** in one `jev.judge("clarity", ...)` request, one Noul per field that exists and isn't already flagged: `role`, `location`, and `seniority` only if the user gave one. "Yes" means too ambiguous to search on. The state sent is the raw request, the draft and the Q&A so far.
- **Only flagged fields are asked,** so a round has at most 3 questions and a clear request gets none. A missing `seniority` isn't ambiguous, because a search can cover all levels. That lets "Data Analyst, Bangalore" go straight through, as the spec's first sample run requires.
- **Drafting.** The cheap tier fills a private `QuestionDraft(text, options)`, and code sets `about` and `answer=None`. A question about an unsupported country lists the supported ones, from code.
- **Counting.** Earlier questions with the same `about` are counted: fewer than 2 means ask, 2 means settle.
- **Settling at the cap:**

| Field state after one re-ask | Result |
|---|---|
| Readable but still vague ("Engineer" twice) | Keep the draft's value, and code writes an Assumption. No LLM call. |
| `location` or `country` null | Country-wide in a new `default_country` setting (`us`), with an Assumption |
| `country` named but unsupported ("Tokyo") | Abort: no source has data there |
| `role` null ("asdf") | Abort: nothing to search for |

- **An abort** writes no `hiring_request`, logs a `route` entry with the reason, and goes to END. Runtime's `derive_status` reports `aborted`.

Decided while writing the LLD:
- **Assumptions are written only when `clarity_check` finishes,** so a field settled in one pass and cleared in a later one leaves no stale Assumption.
- **`location` falls back to the country code** when defaulted, since `HiringRequest.location` must be non-blank.
