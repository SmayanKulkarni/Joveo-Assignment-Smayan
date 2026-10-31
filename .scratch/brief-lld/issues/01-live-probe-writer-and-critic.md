# Live probe of the writer and critic

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

Analysis code isn't built, so what do a throwaway script and hand-built Stats from the 100 Adzuna and 25 USAJOBS fixture Postings show?

- Does the writer cite only real Stat ids, and does it keep figures in its prose faithful to them?
- Does Jev separate supported Insights from deliberately unsupported ones, and with what scores?
- Does a critic request stay under Jev's 32 KB limit, given the Evidence it has to carry?
- What output token limit does the writer need?

This gathers facts for the decisions below and decides nothing. It spends no Adzuna quota, and the script isn't kept.

## Answer

Run on 2026-10-31 with `minimax/minimax-m3.1-flash` and `typesafe/jev-1.14`, for about $0.09 of OpenRouter credit and no job API calls.

### Setup and its limits

- 46 hand-built Stats in Analysis's id and label shape, from one Adzuna fixture of 50 Postings. Skills came from a fixed word list, not real Extractions. USAJOBS wasn't used, so federal pay is untested.
- A rough draft schema and a hand-written prompt, not a design. Nothing here fixes either.
- 4 full runs and 1 at `max_tokens=2048`, 3 thin (8 Postings) and 2 zero through `Tiers`, then 5 raw zero calls.
- The prompt said Washington DC, but the fixture is mostly Manhattan and New Jersey. The thin Caveat also said 50 Postings when the Sample had 8, and the writer repeated that. Neither affects what was measured.
- The number check ignores single digits, so it can miss small wrong counts. Treat the figure result as strong, not proven.

### The writer

| Question | Result |
|---|---|
| Invented Stat ids | 0 across all 8 successful runs |
| Figures in no Stat | None. The only ones flagged were 50 and 500, both from the prompt's Caveats |
| Figures from a Stat it didn't cite | 1 run, where a summary landed in `job_title.value` |
| Parts with no citation at all | 0 to 2 per run |
| Time and size with Stats | 5 to 11 s, 1,215 to 2,476 output tokens, no reasoning tokens |
| Token limit | 2,048 worked for the full run at 1,523, but a thin run reached 2,476, so 2,048 is too tight |

Three failures the schema let through:

- **Empty or wrong recommendations.** In the 4 full runs at 8,192 tokens, `job_title.value` was empty in 3 and held a summary in the fourth. `salary_band.value` was empty in 2. A plain `str` validates all of these. The prompt's "leave lists empty if thin" rule may be leaking into full runs, but this wasn't isolated.
- **Free-text fields.** `dimension` came back as "Demand" and "Title and Seniority", and once as "data_availability".
- **`value` holds prose.** Bands appeared as "$133,676 - $203,199", "133,676-203,199" and a sentence. Titles and bands can come from code instead.

**The outlook isn't stable.** On the same input the full runs gave competitive 4 times and hard to fill once. The thin runs gave favourable once and competitive twice. One raw zero-Posting call answered **favourable with no Postings at all**. Reasons cite employer spread and recency in both directions.

**Thin Samples don't change the writer's behaviour.** With 8 Postings it wrote the maximum of 8 Insights, a salary band, and up to 9 top skills, despite the prompt's rule. Figures stayed honest, but the volume didn't shrink.

### Zero Postings

Both `Tiers` calls failed, after 164 and 464 s, using 25K to 52K tokens each and about $0.03.

The cause is a whitespace runaway. In the raw repeat, 1 of 5 calls ran to `finish_reason=length` at 8,192 tokens, with 43,564 characters that were 99% whitespace and invalid JSON. The other 4 finished in 156 to 454 tokens. No call with Stats did this.

The feedback retry makes it worse, because it resends the whole bad output as input. This is a Kernel `Tiers` behaviour, so any strict-schema call that runs away pays the same way.

### The critic

Scores are Jev's `p_yes`, and the cut is 0.5. The states and questions below were tried on 12 labelled claims and the 6 Insights from one real draft.

| State and question | Exact claims passed | Bad claims rejected | Real writer Insights passed |
|---|---|---|---|
| Stats only, strict wording | 3 of 3 (0.83 to 0.98) | 7 of 8 | 1 of 6 |
| Stats + 20 Postings, strict | 3 of 3 | 7 of 8 | 0 of 6 |
| Stats + all Postings, strict | 3 of 3 | 7 of 8 | 0 of 6 |
| Stats + hiring request, loosened wording | 3 of 3 (0.92 to 0.97) | **8 of 8** (0.01 to 0.07) | 3 of 6 |

- **A strict critic rejects accurate writing.** The real Insights were accurate, yet scored 0.04 to 0.64. Used as written, the revise loop would mostly spin to its cap.
- **Wording mattered most.** The loosened question names the request as a source, allows descriptive words, and names estimated-as-advertised as false. That last case passed the strict wording at 0.65 and scored 0.07 after.
- **Long claims score lower.** Two single-figure claims scored 0.94 and 0.89. The real Insights stating many figures scored 0.16 and 0.17, even loosened. They also add judgement such as "can add staffing flexibility". Which of the two lowers the score wasn't separated.
- **Postings don't help.** Adding them changed no outcome on the labelled claims, and lowered real Insights' scores.
- **My "paraphrase" label was doubtful.** "Python is the most widely requested skill" cited only Python's Stat, which can't show rank, so it's left out of the table's counts. It scored 0.06 strict and 0.42 loose.
- **Cuts remain untuned.** These 20 claims show direction and aren't a basis for fixing a threshold.

**Size:** Stats only tops out at 2 KB per Insight. All Stats and all Insights in one state is 8.9 KB. With all Postings a request reaches 30.5 KB, and the largest was truncated, so Jev's limit only matters if Postings are sent. Calls took 1 to 3 s in total.

### What the open tickets should weigh

Facts only. The decisions remain the user's.

- [The Market Brief schema](02-brief-schema.md): empty recommendations, free-text `dimension`, and prose in `value`.
- [Confidence Tag rules](03-confidence-tag-rules.md) and [Thin and empty Samples](07-thin-and-empty-samples.md): the writer doesn't adjust to thin evidence on its own.
- [Hiring Outlook rules](04-hiring-outlook-rules.md): an LLM-chosen outlook varied on identical input and said favourable at zero.
- [Thin and empty Samples](07-thin-and-empty-samples.md): an LLM call at zero is slow, failure-prone and has nothing to say.
- [Writer failures and bad citations](08-writer-failures-and-bad-citations.md): citations held up, while whitespace runaway and the size of the feedback retry didn't.
- [The critic](09-critic.md): Stats-only state, loosened wording, and claim length.
- [Brief prompts](11-prompts.md): the first prompt's outcomes above are the write-up's "what changed after testing" starting point.
