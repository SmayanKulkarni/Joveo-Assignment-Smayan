# Write docs/lld/analysis.md

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01, 02, 03, 04, 05, 06, 07, 08, 09

## Question

Assemble the resolved tickets on this map into `docs/lld/analysis.md`, in the shape of `docs/lld/collection.md` and including a build checklist, and make the other docs agree with it. Run `langchain-router` first for the framework details: `Send`, the fan-in and the reducer.

Known changes elsewhere:
- **Kernel:** `skill_aliases` on `State` and the owner table, `LLMExhausted.bad_output`, the Caveat list.
- **Runtime:** `normalise_skills` in the edges and owners, `ExtractBatch` in `ALLOWED_MSGPACK`, the `fan_out` hand-on.
- **HLD:** §3 row E, §4's diagram, §5, §11's sequential extraction, §12's Analysis row.
- **Collection, Gateway:** mark their Analysis hand-ons as settled.
- **Glossary:** Extraction, and advertised vs estimated pay.
- **future-scope.md:** an Analysis section.

## Answer

[docs/lld/analysis.md](../../../docs/lld/analysis.md) is written, with one build checklist, since Analysis has nothing to hold back for later passes. The other docs above agree with it, and `future-scope.md` has an Analysis section.

No code changed. `State`, `analysis/types.py`, `LLMExhausted` and `runtime/graph.py` keep their old shapes until step 1 of the checklist.

Decisions made while writing, beyond the tickets:
- **`relevance` can't take the zero path,** since its Sample is at least the target of 20, so it keeps its existing targets. Only `low_data_review` needs `stats`.
- **`.unknown_share` is what Postings with no company count towards,** rather than dropping them from the split.
- **With no Postings in the older window, the trend is `rising`,** because a ratio can't be computed and every Posting being new is what the data shows. Its label still says it counts ads still live.

Unproven until a live Run: that advertised Adzuna pay with an `unknown` period is annual (the fixtures have only estimates), and whether the tight merge prompt holds on roles beyond data engineering, since the probe covered only that role.
