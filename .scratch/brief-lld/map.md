# Brief LLD

Label: wayfinder:map
Parent: [Talent Market Scout: HLD](../talent-scout-hld/map.md) (component F in [docs/HLD.md](../../docs/HLD.md) §3, §4)

## Destination

`docs/lld/brief.md`: an LLD of Brief precise enough to build straight from, covering `write_brief`, `critic`, `render` and building the Run Notes, with nothing left to decide. Building the code is a separate effort after this map.

## Notes

- Domain: Brief turns Stats, Caveats and the run's slices into a Market Brief, as JSON and Markdown. The LLM chooses and phrases Insights but never invents figures. Vocabulary: `GLOSSARY.md`. Spec: `Joveo_Talent_Market_Agent- Assessment.pdf` (Step 6). Deadline Mon 2 Nov 2026, 9:00 AM, so this map stays lean.
- Fixed upstream: [docs/lld/kernel.md](../../docs/lld/kernel.md) §3 (Stat ids expand into Evidence, LLM-schema policy), §4, §6, §7 (critic routing), §9 (every Caveat in the Run Notes), §12 (Tiers), §14 (replay banner), [docs/lld/analysis.md](../../docs/lld/analysis.md) §8, §9, §10, §14, [docs/lld/collection.md](../../docs/lld/collection.md) §11, §15, [docs/lld/request-plan.md](../../docs/lld/request-plan.md) §8, [docs/lld/runtime.md](../../docs/lld/runtime.md) §3, §4, §10, HLD §5, §6.
- Skills: `langchain-router` first, then what it points to (per `CLAUDE.md`).
- The user resolved the first two `grilling` tickets live, then on 2026-10-31 told the agent to make every remaining decision itself and finish the map. So tickets 04 to 11 keep their `grilling` type but were decided by the agent, and each says so.
- Live calls use `minimax/minimax-m3.1-flash` and `typesafe/jev-1.14`, spending no Adzuna quota.
- Standing preferences: inherited from the Kernel map (Pydantic v2 everywhere, `uv`, Python 3.12, `src/talent_scout/`, `pytest`, root `.env`).

## Decisions so far

<!-- one line per closed ticket -->

- [Live probe of the writer and critic](issues/01-live-probe-writer-and-critic.md): the writer cites real Stats, but leaves recommendations empty, varies its outlook on identical input and can run away at zero Postings, while a strict critic rejects accurate Insights and loosened wording fixes much of that.
- [The Market Brief schema](issues/02-brief-schema.md): the LLM drafts only the Summary and 1 to 8 Insights with their Stat ids, and `render` builds the typed `MarketBrief` in code, with Evidence as the union of cited Stats' Postings and one new `State` field, `brief_draft`.
- [Confidence Tag rules](issues/03-confidence-tag-rules.md): code rates each cited Stat (High at 30+ Postings from 10+ employers, Medium at 10+ from 5+), an Insight takes its weakest Stat, estimated pay, snippet skills and old data cap it at Medium, and only Insights are tagged.
- [Live check of the draft design](issues/13-live-check-of-the-draft-design.md): a strict figure and coverage check exhausted 7 of 8 runs, while the adopted design got 8 of 8 valid drafts and 51 of 54 Insights confirmed, and a runaway can happen with Stats too.
- [Hiring Outlook rules](issues/04-hiring-outlook-rules.md): code rates it from employers, how demanding the profile is and the trend, says it's a proxy because Postings don't show candidates, and defaults to a stated Competitive under 20 Postings.
- [Client Recommendations](issues/05-client-recommendations.md): code picks the title by employers, the band as the middle 50% of advertised then estimated pay at the request's level, and the top 5 skills, each `None` when it lacks evidence.
- [What focus changes in the Brief](issues/06-what-focus-changes.md): `focus` sorts Insights and steers the writer's emphasis only, and code adds an Insight for any Dimension left uncovered.
- [Thin and empty Samples](issues/07-thin-and-empty-samples.md): zero Postings makes no LLM or Jev call and gives a code-built Brief, and under 10 Postings caps Insights at 3 with no coverage rule.
- [Writer failures and bad citations](issues/08-writer-failures-and-bad-citations.md): a per-Run validator retries unknown ids and invented figures through Kernel's feedback retry, transient failure stops the Run, and bad output from every model gives a rule-written draft with a Caveat.
- [The critic](issues/09-critic.md): Jev judges each Insight against its cited Stats at 0.5, up to 2 revisions replace only flagged Insights, and what's unconfirmed at the cap ships capped at Medium with a Caveat.
- [render and the Run Notes](issues/10-render-and-run-notes.md): Markdown leads with answers, each part points to an Evidence list by reference, and Run Notes come from the slices, with a banner on replay.
- [Brief prompts](issues/11-prompts.md): the LLD fixes the writer's input order and rules, values go in formatted, wording stays in `brief/prompts.py`, and two Analysis Caveats get reworded.
- [Write docs/lld/brief.md](issues/12-write-brief-lld-doc.md): the LLD is written and the upstream docs and glossary are in line with it.

## Not yet specified

Nothing: the destination is reached.

## Out of scope

- Writing the Brief code: separate build effort after this map.
- The Supervisor stretch goal: ruled out in HLD §1.
- How long-term memory preferences reach the Brief: Long-term memory LLD.
- Choosing the three sample runs, the `samples/` transcripts and the write-up: Delivery.
