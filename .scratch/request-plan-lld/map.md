# Request & Plan LLD

Label: wayfinder:map
Parent: [Talent Market Scout: HLD](../talent-scout-hld/map.md) (component C in [docs/HLD.md](../../docs/HLD.md) §3, §4)

## Destination

`docs/lld/request-plan.md`: an LLD of Request & Plan precise enough to build straight from, covering pass 1 (`intake`, `clarity_check`, `clarify`, `plan`, a pass-through `plan_review`) and pass 2 (the real `plan_review`, `focus`), with a stated seam for pass 6 preferences and nothing left to decide. Building the code is a separate effort after this map.

## Notes

- Domain: Request & Plan turns `request_text` into a final Hiring Request and an approved Search Plan, pausing for the user only when it has to. Vocabulary: `GLOSSARY.md`. Spec: `Joveo_Talent_Market_Agent- Assessment.pdf`. Deadline Mon 2 Nov 2026, 9:00 AM, so this map stays lean.
- Fixed upstream: [docs/lld/kernel.md](../../docs/lld/kernel.md) §3 (LLM-schema policy), §7 (routing), §11 (Jev), §12 (Tiers), [docs/lld/runtime.md](../../docs/lld/runtime.md) §3 (stage contract), §5 (Pause protocol), [docs/lld/gateway.md](../../docs/lld/gateway.md) §3 (`Fetch`, `ADZUNA_CURRENCY`), HLD §4, §6.
- Skills: `langchain-router` first for any framework question (per `CLAUDE.md`); `grilling` + `domain-modeling` for grilling tickets.
- Standing preferences: inherited from the Kernel map (Pydantic v2 everywhere, `uv`, Python 3.12, `src/talent_scout/`, `pytest`, root `.env`).
- Tiers are fixed by the HLD: cheap for parsing and question drafting, strong for planning.
- All tickets were resolved in one grilling session, in two rounds, on 2026-10-31.

## Decisions so far

<!-- one line per closed ticket -->

- [Request parsing and the clarify loop](issues/01-request-parsing-and-clarify-loop.md): `intake` parses into a nullable `RequestDraft` and `clarify` returns to it, `clarity_check` alone writes the final `hiring_request`, routers need no decision field, and `HiringRequest` gains an inferred `country`, so unsupported countries are caught up front.
- [Clarity check and the re-ask cap](issues/02-clarity-check-and-re-ask-cap.md): code flags missing fields, Jev judges role, location and any given seniority with "yes" meaning ambiguous, only flagged fields are asked, and at the cap a field settles with an Assumption or the Run aborts.
- [Search Plan and its limits](issues/03-search-plan-and-limits.md): the strong tier fills `SearchPlan` directly, with limits on the Kernel type so the LLM, an edit and `broaden` share one set of checks.
- [Pause payloads and answers](issues/04-pause-payloads-and-answers.md): `clarify` answers match by position with blanks counting as vague; `plan_review` shows the plan and Assumptions, and validators require `plan` on edit and `feedback` on reject.
- [What focus changes](issues/05-what-focus-changes.md): nothing in the search; Brief uses it for emphasis, and the CLI accepts `salary` as an alias.
- [Prompts](issues/06-prompts.md): the LLD fixes each prompt's inputs and rules, and the exact wording lives in `request_plan/prompts.py`, tuned during the build.
- [Write docs/lld/request-plan.md](issues/07-write-request-plan-lld-doc.md): the LLD is written and the HLD, Kernel, Runtime, Gateway and future-scope docs agree with it.

## Not yet specified

## Out of scope

- `broaden`, `low_data_review` and their fields: Collection LLD.
- Insight emphasis from `focus`, and rendering Assumptions in the Run Notes: Brief LLD.
- What preferences contain and how they fill draft fields: Long-term memory LLD.
- Writing the Request & Plan code: separate build effort after this map.
