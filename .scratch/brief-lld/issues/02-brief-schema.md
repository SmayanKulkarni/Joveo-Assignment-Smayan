# The Market Brief schema

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01

## Question

What are `MarketBrief` and its parts, which fields does the LLM fill in its draft, and which does code fill, including how cited Stat ids expand into Evidence? How many Insights are allowed, and what new `State` fields does Brief add?

## Answer

Decided by grilling. Types live in `brief/types.py`.

```python
class BriefDraft(Model):                 # all the LLM fills, for now
    summary: str
    summary_stat_ids: list[str]          # at least 1
    insights: list[InsightDraft]         # 1 to 8; each is text + stat_ids (at least 1)

class MarketBrief(Model):
    hiring_request: HiringRequest
    replayed: bool
    summary: str
    summary_stat_ids: list[str]
    insights: list[Insight]              # text, dimension, stat_ids, evidence, confidence
    recommendations: ClientRecommendations
    outlook: HiringOutlook               # rating, reason, stat_ids, evidence
    run_notes: RunNotes
    stats: MarketStats                   # whole, so every cited id can be checked

class ClientRecommendations(Model):      # each has reason, stat_ids, evidence
    job_title: TitleRecommendation | None    # + title
    salary_band: BandRecommendation | None   # + low, high, unit, copied from Stats by code
    top_skills: SkillsRecommendation | None  # + skills

class RunNotes(Model):
    questions: list[ClarifyingQuestion]
    assumptions: list[Assumption]
    final_plan: SearchPlan               # state.current_plan
    earlier_plans: list[SearchPlan]
    postings_analysed: Evidence          # the Sample
    caveats: list[str]                   # messages only: state.py imports this file, so no RunLogEntry
```

- **`render` alone turns the draft into the Brief,** and so alone expands Evidence. `critic` reads the draft and Stats directly.
- **Evidence** is the union of the cited Stats' Postings: what a part rests on, not what's behind each figure. A share never gives a count of 0: `comp.*_share` Evidence is its denominator, so 0% disclosed still rests on every Adzuna Posting, and other shares are omitted when empty (corrected from the real Stats while resolving [Confidence Tag rules](03-confidence-tag-rules.md)).
- **`dimension`** is the first cited Stat's, so the LLM has no field to get wrong.
- **`hiring_request`** is there because broadening can change what the plan implies. **`replayed`** shows a replay in `brief.json` alone. There's no date, since a clock would make replayed Briefs differ.
- **"2 to 3 sentences"** stays in the prompt, since a validator would retry over abbreviations. The final `insights` has no minimum.
- **`State`** gains only `brief_draft: BriefDraft | None`, replaced by `write_brief` on each revision.

Left to later tickets:

- [Confidence Tag rules](03-confidence-tag-rules.md), [Hiring Outlook rules](04-hiring-outlook-rules.md) and [Client recommendations](05-client-recommendations.md) add a draft field only if the LLM should write that part.
- [Thin and empty Samples](07-thin-and-empty-samples.md): `outlook` is required even at zero Postings, a zero-Posting Run must avoid a draft with no Insights, and thin runs may tighten the cap of 8.
- [The critic](09-critic.md) names its own `State` fields.
- [Render and Run Notes](10-render-and-run-notes.md) adds the `total` disclosure and places the replay banner.
- [Write the Brief LLD doc](12-write-brief-lld-doc.md): required fields break the `MarketBrief()` stub in `runtime/testing.py`.
