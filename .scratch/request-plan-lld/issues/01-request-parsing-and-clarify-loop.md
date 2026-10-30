# Request parsing and the clarify loop

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

How does free text become a Hiring Request when the text may be incomplete, and where do Clarifying Question answers get applied?

- What `intake` parses into, given `HiringRequest` requires `role` and `location`.
- Which node applies answers. Kernel §4 says `intake` refines `hiring_request` after answers, while HLD §4 and Runtime §4 wire `clarify → clarity_check`.
- Which node writes `hiring_request`, and how the router after `clarity_check` decides.
- Where an unsupported country is caught.

## Answer

Decided by grilling.

- **`RequestDraft`.** `intake` parses into a private model in `request_plan/types.py` where every field can be null. Parsing "Data analyst" straight into `HiringRequest` would fail validation on every retry until `LLMExhausted` stopped the Run, so an incomplete request would look like a backend failure.
- **`clarify` returns to `intake`.** `intake` re-parses `request_text` plus every answered question and writes a new draft. `clarity_check` then only judges and drafts questions, and doesn't also have to parse. This changes one edge in Runtime §4 and the HLD §4 diagram, and resolves their disagreement with Kernel §4.
- **`hiring_request` means final.** Only `clarity_check` writes it, once nothing is left to ask. Everything before that reads `request_draft`. This changes the owner table in Kernel §4.
- **No decision field.** The router reads state directly: any unanswered question → `clarify`, `hiring_request` set → `plan`, neither → END. Runtime §4 gains the END target for `clarity_check`.
- **`country`.** `RequestDraft` and `HiringRequest` gain a `country` the LLM infers ("Texas" → `us`, "Bangalore" → `in`). A null or unsupported country counts as an ambiguous location. Without this, a bad country fails only when `Fetch` validates it, after the user has approved a plan.
- **`ADZUNA_CURRENCY` moves to `kernel/types.py`,** with `gateway/types.py` importing it, since stage `types.py` modules may import only `kernel.types`.
- A location of just "Remote" gets asked which country. "India" is a valid location with `country = in`.
