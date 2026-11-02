# How a Customer Profile shapes a Run

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [What a Customer Profile holds](16-what-a-customer-profile-holds.md)

## Question

Where does a Run read the Customer Profile, and what is it allowed to change?

- `intake`: skip a Clarifying Question the profile already answers (currency, country), and record it as an Assumption that came from the profile.
- Planning: start the Search Plan from the titles, places and sources that worked before. The plan approval Pause shows what came from the profile.
- Collection and relevance: hints from titles rejected before for this Customer.
- Brief: a line comparing this Run with the Customer's earlier Runs for the same role, built only from stored Stats.
- Matching: what the profile adds to it.
- Limits: a Run reads only its own Customer's profile. The profile only sets defaults and never overrides what the CSM typed. Every effect it has shows up in the Run Notes.
- The state slice (`preferences` in `future-scope.md`), and which nodes read it. Load `langchain-router` first.

## Answer

Decided by the agent alone on 2026-11-02, at the user's request, with no grilling. The decisions are in [Final decisions](../final-decisions.md#how-a-customer-profile-shapes-a-run).
