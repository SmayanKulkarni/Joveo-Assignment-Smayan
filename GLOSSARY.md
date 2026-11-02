# Talent Market Scout

An agent a customer success manager uses for the job seekers they look after: it turns a hiring request and resume into an evidence-backed market brief and a personal recommendation to pass on.

## Language

### People

**CSM**:
A customer success manager, the only person who signs in. A CSM keeps many Customers and works on their behalf.
_Avoid_: User (when a specific role is meant), account

**Customer**:
One job seeker a CSM works for. A Customer belongs to exactly one CSM, never signs in, and owns the resumes, findings, Assumptions and preferences kept about them.
_Avoid_: Candidate, Client

### Resumes

**Resume**:
The one current record of what a Customer has done: their roles, skills and years. A new upload replaces it.

**Match**:
One Posting judged against a Resume, with the reasons for its place in the ranking.

**Customer Profile**:
The defaults learned from a Customer's earlier Runs, such as their usual role, places and currency, which their CSM can see, change and clear. It holds only what Runs show, never the Resume's facts.
_Avoid_: Preferences, memory

### Inputs

**Hiring Request**:
The role, location and optional details (seniority, employment type, remote/hybrid, currency, purpose) a user asks the agent to research.
_Avoid_: Query, job request, search

**Clarifying Question**:
One of 1–3 targeted questions the agent asks when a Hiring Request is too ambiguous to search on.
_Avoid_: Follow-up, prompt

**Assumption**:
A gap in the Hiring Request the agent filled itself (because the user's answer stayed vague, or from the Resume or Customer Profile) and recorded in the Run Notes.

**Search Plan**:
The title variants, one or more places (or the whole country) and radius, date range and target number of Postings the agent intends to fetch.
_Avoid_: Query plan, strategy

### Evidence

**Posting**:
One real job advertisement returned by a jobs source, identified by its source and source ID.
_Avoid_: Job, listing, ad, result

**Remote Posting**:
A Posting from Arbeitnow marked as remote work. It is shown to users anywhere, whatever the job's location, and doesn't promise that the employer can hire there.

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

**Extraction**:
The facts the LLM read from one Posting: skills as written, seniority, years of experience and employer type. Any skill or year not found in the Posting's text is dropped by code.
_Avoid_: Analysis, parse

**Advertised pay**:
A salary the employer stated, as opposed to **Estimated pay**, which is the jobs source's own guess at a salary (Adzuna's `salary_is_predicted`). The two are never pooled, and only Advertised pay counts as disclosed.

**Domain**:
The broad occupational area of a Posting (e.g. IT, engineering, marketing), taken from the jobs source's own category.
_Avoid_: Industry, sector, vertical

**Region**:
Where a Posting is, as the jobs source's own place hierarchy from country down to town.
_Avoid_: Area, geography

### Output

**Market Brief**:
One of a Run's two deliverables, about the market rather than the person: Summary, Insights, Hiring Outlook and Run Notes.
_Avoid_: Report, analysis, output

**Insight**:
A single finding in the Market Brief, carrying a Confidence Tag and the Evidence it rests on.
_Avoid_: Finding, observation

**Customer Recommendation**:
One of a Run's two deliverables, personal to the Customer: the job title, salary band and top skills to aim for, tied to the Evidence behind them, plus ranked Matches when the Customer has a Resume.
_Avoid_: Advice, suggestion

**Evidence**:
The count and IDs of the Postings an Insight or recommendation is based on.
_Avoid_: Source, citation

**Confidence Tag**:
High, Medium or Low, stating how strongly the Evidence supports an Insight.

**Hiring Outlook**:
Exactly one of Favourable, Competitive or Hard to fill, with a one-line reason. Postings show demand and not candidates, so it estimates the talent market rather than measuring it.
_Avoid_: Difficulty, rating

**Run Notes**:
The record of Clarifying Questions and answers, the final Search Plan, Postings analysed, Assumptions made and Caveats raised.
_Avoid_: Log, metadata

**Caveat**:
A limitation found during a Run that affects how far the user can trust the Market Brief, such as Postings lost, too little or old data, or a judgement made without Jev's probabilities. Always in the Run Notes; the screen shows at most two as plain lines. Backend errors are never Caveats.
_Avoid_: Warning, error, disclaimer

### Process

**Run**:
One end-to-end attempt to answer a Hiring Request, filed under one Customer, which may span several sessions across Pauses.
_Avoid_: Job, session, execution

**Attempt**:
One pass of fetching and judging Postings under one Search Plan.
_Avoid_: Try, round, iteration

**Pause**:
A point where a Run stops and waits for the user: clarification, plan approval or low-data review.
_Avoid_: Interrupt, checkpoint, stop

**Step**:
One user-level stage of a Run in the web UI, such as "Search job boards", merging one or more graph nodes under a friendly label.
_Avoid_: Node (in the UI), stage

**Demo Run**:
A Run on the scripted, paced demo graph, using no LLM or jobs API, kept apart from real Run history so the web UI can be built and checked offline.
_Avoid_: Mock run, fake run
