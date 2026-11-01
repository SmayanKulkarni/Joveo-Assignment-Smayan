# 16: A Brief you can read at a glance

**What to build:** the answer in seconds, with detail on request. Spec: [Web UI LLD](../../../docs/lld/web-ui.md) §9, [Brief LLD](../../../docs/lld/brief.md).

**Blocked by:** 15: Subtle neumorphic look and readable labels

**Status:** done

- [x] `brief/glance.py` with `reader_notes`, at most two by the §9 order, on `RunDetail` as `glance`
- [x] Four tiles, each with a "Why" fold holding its reason and Evidence
- [x] Reader notes under the tiles, and the Weak Sample notice only through them
- [x] Three Insights first, highest confidence first, then "Show all", with reason and Evidence folded
- [x] Run Notes and Postings under a closed "How this was researched", and attribution always visible
- [x] `InsightDraft.text` asks for at most 20 words, and `outlook()` says "an entry level"
- [x] Tests: the order and the limit of two, each note on a real Brief, every Caveat still in `brief.md`. Both Briefs in `runs/` open
