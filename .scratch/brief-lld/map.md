# Brief LLD

Label: wayfinder:map
Parent: [Talent Market Scout: HLD](../talent-scout-hld/map.md) (component F in [docs/HLD.md](../../docs/HLD.md) §3, §4)

## Destination

`docs/lld/brief.md`: an LLD of Brief precise enough to build straight from, covering `write_brief`, `critic`, `render` and building the Run Notes, with nothing left to decide. Building the code is a separate effort after this map.

## Notes

- Domain: Brief turns Stats, Caveats and the run's slices into a Market Brief, as JSON and Markdown. The LLM chooses and phrases Insights but never invents figures. Vocabulary: `GLOSSARY.md`. Spec: `Joveo_Talent_Market_Agent- Assessment.pdf` (Step 6). Deadline Mon 2 Nov 2026, 9:00 AM, so this map stays lean.
- Fixed upstream: [docs/lld/kernel.md](../../docs/lld/kernel.md) §3 (Stat ids expand into Evidence, LLM-schema policy), §4, §6, §7 (critic routing), §9 (every Caveat in the Run Notes), §12 (Tiers), §14 (replay banner), [docs/lld/analysis.md](../../docs/lld/analysis.md) §8, §9, §10, §14, [docs/lld/collection.md](../../docs/lld/collection.md) §11, §15, [docs/lld/request-plan.md](../../docs/lld/request-plan.md) §8, [docs/lld/runtime.md](../../docs/lld/runtime.md) §3, §4, §10, HLD §5, §6.
- Skills: `langchain-router` first, then what it points to (per `CLAUDE.md`).
- **The user resolves every decision on this map live.** Unlike the Analysis map, nothing here is delegated: every `grilling` ticket is a real exchange with the user, and the agent never answers its own questions. Task tickets gather facts or record decisions and decide nothing.
- Live calls use `minimax/minimax-m3.1-flash` and `typesafe/jev-1.14`, spending no Adzuna quota.
- Standing preferences: inherited from the Kernel map (Pydantic v2 everywhere, `uv`, Python 3.12, `src/talent_scout/`, `pytest`, root `.env`).

## Decisions so far

<!-- one line per closed ticket -->

## Not yet specified

- Any Caveats Brief itself raises, which hang on how confidence, recommendations, bad citations and the critic are decided.
- Whether the upstream docs need changes beyond the known ⏳ items, which the write-up ticket will sweep once the shape is known.

## Out of scope

- Writing the Brief code: separate build effort after this map.
- The Supervisor stretch goal: ruled out in HLD §1.
- How long-term memory preferences reach the Brief: Long-term memory LLD.
- Choosing the three sample runs, the `samples/` transcripts and the write-up: Delivery.
