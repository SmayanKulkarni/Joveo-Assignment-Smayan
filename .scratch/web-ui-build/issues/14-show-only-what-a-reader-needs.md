# 14: Show only what a reader needs

**What to build:** the live view and trace show plain progress and no log text. Spec: [Web UI LLD](../../../docs/lld/web-ui.md) §7.

**Blocked by:** none

**Status:** done

- [x] `LogKind.result`, written by `collect`, `relevance` and `broaden`, and `NodeDone.results`
- [x] Turns and the trace show results only, and `fromLog` filters on `kind`
- [x] Refused, bad-argument and unknown-tool cards read "Skipped: search limit reached" or "Didn't run", while the model's text is unchanged
- [x] Pills use source names
- [x] Remove the "Some live text wasn't kept" line and `gap`
- [x] Contract file updated. Vitest: no route name or plan diff reaches a turn. Old Runs still open
