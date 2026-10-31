# 02: A zero-Posting Run produces a real Brief

**What to build:** the tracer bullet. A Run whose Sample is empty goes through the real Brief nodes, makes no LLM or Jev call, and ends in `done` with a `brief.json` and `brief.md` a reader can trust: it says no findings exist and shows exactly what was searched. Spec: [Brief LLD](../../../docs/lld/brief.md) §4, §5 (`empty_draft`), §11, §12, §13, §15 pass 1 step 8.

**Blocked by:** 01: Prefactor and the Brief contract

**Status:** done

Scope limits, each lifted by a later ticket:
- The Outlook is the stated Competitive default (04) and every recommendation is `None` (05).
- `critic` is the pass-through from §10, so `after_critic` goes to `render` and nothing is capped (09).
- A Run with Postings fails loudly and can be resumed until ticket 03. It must not print "no findings" for a Run that has Postings.

- [x] The Brief's `make_nodes(deps)` and `ROUTERS` are in the graph and override the stubs
- [x] At zero Postings, no LLM or Jev call happens, and the Summary reads as in §11
- [x] A graph test with other stages stubbed reaches `done` with both files written
- [x] The Markdown has every section in §12's order, with "Not enough evidence to suggest…" for each `None`
- [x] Run Notes are whole: questions, assumptions, focus, final and earlier plans, Postings by source, one match-count line per title and source, and every Caveat in order as written
- [x] The jobs data attribution line appears only when an Adzuna Posting is in the Sample
- [x] The replay banner appears only on replay
- [x] Two renders of the same state give identical bytes, with no clock anywhere in the Brief
- [x] `write_brief` and `render` write the run log `note` entries in §13
