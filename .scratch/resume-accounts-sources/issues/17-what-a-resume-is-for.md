# What a Resume is for

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

When a CSM uploads a Customer's resume and asks for relevant jobs, what kind of Run is that, and what does it produce for the CSM to pass on?

- The system today answers a Hiring Request with a Market Brief for a client, which is the employer's side. A resume asks the job seeker's question. Pick one:
  - **A new kind of Run** (for example a Job Match Run) with its own small graph or branch, ending in a ranked list of Matches with reasons instead of a Market Brief.
  - **A feeder**: the resume fills in a Hiring Request (titles, places, seniority), and the normal Run produces a Market Brief plus a ranked list.
  - **Both**: the ranked list first, with an offer to run a Market Brief on the best title.
- Which existing stages it reuses (intake, plan approval Pause, Collection, relevance judging, Extraction) and which it skips (Stats, Hiring Outlook, Client Recommendations?).
- What the Run Notes and Pauses look like for it, and whether the plan approval Pause stays.
- What a Market Brief means when it's filed under a job seeker. Every Run belongs to a Customer, but Client Recommendations advise an employer's job ad. Keep them, reword them or drop them for these Runs?
- Is a resume stored per Customer and reused across Runs (one current resume, or many), or used once and dropped?
- Does it feed the Customer Profile?
- New glossary terms (Resume, Match, maybe Job Match Run), and what to avoid calling them.

This is on the frontier: it needs no research to decide. Run `grilling` and `domain-modeling`.

## Answer

Grilled with the user on 2026-11-02. The agent first proposed a separate kind of Run with no Brief, and the user rejected that: a Run keeps its Brief and its Clarifying Questions, and has two deliverables.

1. **One kind of Run.** A resume doesn't start a different Run. Every Run goes intake, clarify, plan, plan approval, Collection, Extraction and Stats as today, plus a new matching stage, and produces two deliverables.
2. **Market Brief:** about the market. Summary, Insights, Hiring Outlook and Run Notes. Hiring Outlook keeps its three values and gains a fixed line on what each means for a job seeker. Numbers and logic don't change.
3. **Customer Recommendation:** about the person. The job title, salary band and top skills to aim for (the old Client Recommendation's data, moved out of the Brief), plus the ranked Matches. It has its own screen and downloads, and the system sends nothing to the Customer. The term Client is retired.
4. **No Resume is allowed.** A typed request alone gives the Brief and a Customer Recommendation with no Matches, and the Run Notes say why.
5. **The Resume feeds the request.** It fills a draft Hiring Request (title, seniority, place) and anything the CSM types takes priority. `intake` reads both and `clarity_check` asks about whatever is still unclear. Each field taken from the Resume is recorded as an Assumption, so the CSM sees it at plan approval.
6. **Pauses:** all three stay: clarification, plan approval and low-data review.
7. **Keeping resumes.** Each Customer has one current Resume, and a new upload replaces it. Each Run keeps its own copy of the parsed facts it used. Extracted text is stored and the original file dropped.
8. **Correcting parsed facts.** The CSM reviews and edits them on the Resume before any Run, outside the graph. Anything added that isn't in the resume text is marked "added by CSM". A new upload starts fresh and drops those edits.
9. **Resume and Customer Profile stay separate.** The Resume holds what the person has done, read directly by a Run. The profile holds only what's learned from Runs.
10. **Run Notes** stay the same, plus one line naming when the Resume was uploaded and which CSM-added facts were used.
