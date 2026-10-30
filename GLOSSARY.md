# Talent Market Scout

An agent that turns a client's hiring request into an evidence-backed market brief a customer success manager can hand to the client.

## Language

### Inputs

**Hiring Request**:
The role, location and optional details (seniority, employment type, remote/hybrid, currency, purpose) a user asks the agent to research.
_Avoid_: Query, job request, search

**Clarifying Question**:
One of 1–3 targeted questions the agent asks when a Hiring Request is too ambiguous to search on.
_Avoid_: Follow-up, prompt

**Assumption**:
A gap in the Hiring Request the agent filled itself (because the user's answer stayed vague) and recorded in the Run Notes.

**Search Plan**:
The title variants, location scope and radius, date range and target number of Postings the agent intends to fetch.
_Avoid_: Query plan, strategy

### Evidence

**Posting**:
One real job advertisement returned by a jobs source, identified by its source and source ID.
_Avoid_: Job, listing, ad, result

**Relevant Posting**:
A Posting judged to actually match the researched role, as opposed to a keyword collision.

**Duplicate**:
A Posting judged to advertise the same job as another Posting that was kept, from the same or another source, even when advertised in a different place.
_Avoid_: Repost, copy

**Sample**:
The deduplicated set of Relevant Postings a brief is built on.
_Avoid_: Dataset, results

**Sufficiency**:
Whether the Sample is large and relevant enough to analyse, decided by rule against the Search Plan's target.

**Stat**:
One figure computed by code from the Sample, such as a median salary or a top skill's count, carrying its Evidence.
_Avoid_: Metric, number

**Batch**:
A slice of the Sample analysed independently and in parallel with other Batches.
_Avoid_: Chunk, page

**Domain**:
The broad occupational area of a Posting (e.g. IT, engineering, marketing), taken from the jobs source's own category.
_Avoid_: Industry, sector, vertical

**Region**:
Where a Posting is, as the jobs source's own place hierarchy from country down to town.
_Avoid_: Area, geography

### Output

**Market Brief**:
The final structured deliverable: Summary, Insights, Client Recommendations, Hiring Outlook and Run Notes.
_Avoid_: Report, analysis, output

**Insight**:
A single finding in the Market Brief, carrying a Confidence Tag and the Evidence it rests on.
_Avoid_: Finding, observation

**Evidence**:
The count and IDs of the Postings an Insight or recommendation is based on.
_Avoid_: Source, citation

**Confidence Tag**:
High, Medium or Low, stating how strongly the Evidence supports an Insight.

**Hiring Outlook**:
Exactly one of Favourable, Competitive or Hard to fill, with a one-line reason.
_Avoid_: Difficulty, rating

**Run Notes**:
The record of Clarifying Questions and answers, the final Search Plan, Postings analysed, Assumptions made and Caveats raised.
_Avoid_: Log, metadata

**Caveat**:
A limitation found during a Run that affects how far the user can trust the Market Brief, such as Postings lost, too little or old data, or a judgement made without Jev's probabilities. Always shown in the Run Notes; backend errors are never Caveats.
_Avoid_: Warning, error, disclaimer

### Process

**Run**:
One end-to-end attempt to answer a Hiring Request, which may span several sessions across Pauses.
_Avoid_: Job, session, execution

**Pause**:
A point where a Run stops and waits for the user: clarification, plan approval or low-data review.
_Avoid_: Interrupt, checkpoint, stop
