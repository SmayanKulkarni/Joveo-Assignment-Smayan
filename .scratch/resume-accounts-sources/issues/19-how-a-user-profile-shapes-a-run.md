# How a User Profile shapes a Run

Type: grilling
Status: open
Assignee: none
Blocked by: [What a User Profile holds](16-what-a-user-profile-holds.md)

## Question

Where does a Run read the User Profile, and what is it allowed to change?

- `intake`: skip a Clarifying Question the profile already answers (currency, country), and record it as an Assumption that came from the profile.
- Planning: start the Search Plan from the titles, places and sources that worked before. The plan approval Pause shows what came from the profile.
- Collection and relevance: hints from titles the user rejected before.
- Brief: a line comparing this Run with the user's earlier Runs for the same role, built only from stored Stats.
- Resume Runs: what the profile adds to matching.
- Limits: the profile only sets defaults and never overrides what the user typed. Every effect it has shows up in the Run Notes.
- The state slice (`preferences` in `future-scope.md`), and which nodes read it. Load `langchain-router` first.
