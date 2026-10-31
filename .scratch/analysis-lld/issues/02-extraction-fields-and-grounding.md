# What is extracted, and how it stays grounded

Type: grilling (delegated to the agent)
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01

## Question

Which per-Posting facts does the LLM return, and what stops an invented fact reaching a Stat, given that "every number traces back to real postings" is 20% of the marks?

## Answer

Only facts a Dimension needs and code can't get from the Posting:

| Field | Values | Why |
|---|---|---|
| `skills` | `name` plus `requirement`: `must`, `nice` or `unstated` | Skills Dimension, must-have vs nice-to-have |
| `seniority` | `entry`, `mid`, `senior`, `lead`, `executive`, `unknown` | Seniority mix. From the title or explicit wording only, never guessed from years |
| `years_min` | int or null | Typical years of experience, explicit only |
| `employer_type` | `direct`, `agency`, `unknown` | Direct vs staffing split |

Left out: salary (structured fields exist, and an LLM reading amounts out of text is the risk to avoid), location, employment type and work mode (no Dimension uses them).

**Skill names are verbatim.** Normalising inside each Batch can't be consistent across Batches, and it would make a name impossible to check. So extraction copies, and one later step normalises ([Normalising skills](05-normalising-skills.md)).

**Code checks what it can.** A skill whose folded name isn't a whole-word match in the Posting's title and description is dropped and counted. A `years_min` whose number isn't in the text, or that is over 40, becomes null. The probe saw 2% to 10% of skills fail this check depending on Batch size. Those are the very cases that would otherwise become false Evidence.

`seniority` and `employer_type` are judgements, so they can't be checked this way. The spec accepts that, because they're reported as shares, not cited facts.

**Folding keeps `+` and `#`,** so `C`, `C++` and `C#` stay three skills. Whole-word matching stops `R` matching inside another word.

`Extraction` is the stored model, with `ungrounded: int` added, because a branch can't log. The LLM model `PostingFacts` adds `ref` instead. Both share a base so the two can't drift.

USAJOBS Postings get `employer_type = direct` from code in `stats`, since a federal agency hires for itself.
