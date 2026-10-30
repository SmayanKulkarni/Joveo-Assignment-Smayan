# Prompts

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01, 02, 03

## Question

How much of the prompt text does this LLD fix, and what does each prompt get?

## Answer

Decided by grilling.

- **The LLD fixes each prompt's inputs, rules and schema descriptions.** The exact wording lives in `request_plan/prompts.py` and is tuned during the build. The write-up has to say what changed after testing, so the wording should stay easy to change.
- **`intake` (cheap):** `request_text` plus the answered questions, with examples from the spec's cases.
- **Question drafting (cheap):** the draft plus the flagged fields.
- **`plan` (strong):** `hiring_request`, Assumptions, and on a reject the previous plan and feedback. Guidance suggests about 100 target Postings for a broad role, about 30 for a niche one, and `max_days_old` of 30.
- **Jev:** the raw request, the draft and the Q&A.
- **Caveats:** a Jev call with `llm_fallback` or `truncated` logs a Caveat, as Kernel §11 requires. Those are the only Caveats this stage raises.
