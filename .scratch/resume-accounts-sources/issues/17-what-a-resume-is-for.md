# What a Resume is for

Type: grilling
Status: open
Assignee: none
Blocked by: none

## Question

When a user uploads a resume and asks for relevant jobs, what kind of Run is that, and what does it produce?

- The system today answers a Hiring Request with a Market Brief for a client, which is the employer's side. A resume asks the job seeker's question. Pick one:
  - **A new kind of Run** (for example a Job Match Run) with its own small graph or branch, ending in a ranked list of Matches with reasons instead of a Market Brief.
  - **A feeder**: the resume fills in a Hiring Request (titles, places, seniority), and the normal Run produces a Market Brief plus a ranked list.
  - **Both**: the ranked list first, with an offer to run a Market Brief on the best title.
- Which existing stages it reuses (intake, plan approval Pause, Collection, relevance judging, Extraction) and which it skips (Stats, Hiring Outlook, Client Recommendations?).
- What the Run Notes and Pauses look like for it, and whether the plan approval Pause stays.
- Is a resume stored per user and reused across Runs (one current resume, or many), or used once and dropped?
- Does it feed the User Profile?
- New glossary terms (Resume, Match, maybe Job Match Run), and what to avoid calling them.

This is on the frontier: it needs no research to decide. Run `grilling` and `domain-modeling`.
