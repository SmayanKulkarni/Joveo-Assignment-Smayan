# Analysis LLD

Label: wayfinder:map
Parent: [Talent Market Scout: HLD](../talent-scout-hld/map.md) (component E in [docs/HLD.md](../../docs/HLD.md) §3, §4)

## Destination

`docs/lld/analysis.md`: an LLD of Analysis precise enough to build straight from, covering `fan_out`, `batch_extract`, `normalise_skills` and `stats`, with nothing left to decide. Building the code is a separate effort after this map.

## Notes

- Domain: Analysis turns a Sample into per-Posting Extractions and a list of Stats that each carry their Evidence. The LLM extracts, and Python computes every number. Vocabulary: `GLOSSARY.md`. Spec: `Joveo_Talent_Market_Agent- Assessment.pdf`. Deadline Mon 2 Nov 2026, 9:00 AM, so this map stays lean.
- Fixed upstream: [docs/lld/kernel.md](../../docs/lld/kernel.md) §3 (`Stat`, `MarketStats`, LLM-schema policy), §5 (the `extractions` reducer), §9 (Caveats), §10 (msgpack rules), §12 (Tiers), [docs/lld/runtime.md](../../docs/lld/runtime.md) §3, §4 (stage contract, `"analyse"`), §10 (events), [docs/lld/collection.md](../../docs/lld/collection.md) §4, §15 (hand-ons), [docs/lld/gateway.md](../../docs/lld/gateway.md) §7, §17, HLD §5.
- Skills: `langchain-router` first, then `langgraph-fundamentals` for `Send` and reducers (per `CLAUDE.md`).
- **The user delegated every decision on this map to the agent** ("make all decisions yourself, ensure they are rational"), so the grilling tickets were answered from the spec, the upstream LLDs and live probes rather than a live exchange. Each ticket gives its reasoning so any of them can be challenged later.
- Live probes ran on 2026-10-31 on the 100 Adzuna and 25 USAJOBS fixture Postings with `minimax/minimax-m3.1-flash` and `typesafe/jev-1.14`, spending no Adzuna quota. The scripts were throwaway. The findings are in [Live probe of extraction and skill merging](issues/01-live-probe-extraction-and-merging.md).
- Standing preferences: inherited from the Kernel map (Pydantic v2 everywhere, `uv`, Python 3.12, `src/talent_scout/`, `pytest`, root `.env`).

## Decisions so far

<!-- one line per closed ticket -->

- [Live probe of extraction and skill merging](issues/01-live-probe-extraction-and-merging.md): the default token limit fails even 10 Postings, citation slips grow with Batch size, all Adzuna pay in hand is estimated, and a loose merge prompt inflates counts while a tight one doesn't.
- [What is extracted, and how it stays grounded](issues/02-extraction-fields-and-grounding.md): verbatim skills with a requirement, seniority, `years_min`, employer type, with code dropping any skill or year that isn't in the Posting's text.
- [Batching and fan_out](issues/03-batching-and-fan-out.md): at most 20 Postings or 20,000 characters per Batch, 8,192 output tokens, positional refs, and `Send` from pass 1.
- [When extraction fails](issues/04-extraction-failure.md): transient failures stop the Run and resume reruns only the failed Batch, while bad output skips that Batch with a Caveat.
- [Normalising skills](issues/05-normalising-skills.md): one LLM call after the fan-in, in a new `normalise_skills` node, with no Jev veto and every merge listed in the run log.
- [Normalising pay](issues/06-normalising-pay.md): advertised, estimated and federal pay are three separate groups, never pooled, annualised and shown in one currency using a dated fixed-rate table.
- [The Stat catalogue](issues/07-stat-catalogue.md): fixed ids per Dimension, skills ranked by distinct employers, employer type decided per employer, and a trend only on a window of 28 days or more.
- [Caveats and the run log](issues/08-caveats-and-run-log.md): nine Analysis Caveats with fixed triggers, all written by `stats` except the skill-merge one.
- [Prompts](issues/09-prompts.md): the LLD fixes inputs and rules, wording lives in `analysis/prompts.py`, and the probed prompt text is the starting point.
- [Write docs/lld/analysis.md](issues/10-write-analysis-lld-doc.md): the LLD is written and the HLD, Kernel, Runtime, Collection, Gateway, glossary and future-scope docs agree with it.

## Not yet specified

## Out of scope

- Confidence Tags, the Hiring Outlook, Insight emphasis from `focus`, and rendering Caveats and Stats: Brief LLD.
- Whether a Client Recommendation may use an estimated salary band: Brief LLD, with Analysis's labels as its input.
- Choosing the three sample runs within the Adzuna budget: Delivery.
- Writing the Analysis code: separate build effort after this map.
