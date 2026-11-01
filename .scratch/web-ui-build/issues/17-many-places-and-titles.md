# 17: Many places and as many titles as you want

**What to build:** a Run searches several places and any number of titles, and says what it costs. Spec: [Request and Plan LLD](../../../docs/lld/request-plan.md), [Collection LLD](../../../docs/lld/collection.md) §5, [Web UI LLD](../../../docs/lld/web-ui.md) §8.

**Blocked by:** 13: Keep the places the user chose; 15: Subtle neumorphic look and readable labels

**Status:** in progress

- [x] `SearchPlan.locations` with the before-validator for old data, and no `max_length` on titles
- [x] `PLAN_SYSTEM`: same metro means one centre and a wider radius, bare place names, each title one job
- [x] `QUESTION_SYSTEM` offers a place's areas and never "Other"; checkboxes on `about == location`, joined with ", "
- [x] Tools take a checked `location`; per-Attempt cap `max(MAX_FETCHES, titles x places)`; `_fetch_input` lists combinations in order; totals per title and place
- [x] "Places not searched" Caveat, and `calls_left` with the arithmetic at plan review
- [x] Editor: Places chips, no title limit. CLI, Markdown and `where()` print the list
- [ ] Tests (the budget running out reaching the Pause and the live "Mumbai" Run are still to do): old `location` loads, an off-plan place is refused, cap arithmetic, the budget running out reaches the Pause. One live Run: "Mumbai" with Thane ticked
