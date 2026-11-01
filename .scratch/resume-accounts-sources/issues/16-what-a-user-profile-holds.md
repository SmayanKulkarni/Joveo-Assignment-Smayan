# What a User Profile holds

Type: grilling
Status: open
Assignee: none
Blocked by: [Runs that belong to a user](15-runs-that-belong-to-a-user.md), [What a Resume is for](17-what-a-resume-is-for.md)

## Question

What does a User Profile contain, how is it learned from a user's earlier Runs (and resume), and how does the user see and correct it?

- This is the HLD's Long-term memory component (I), and it answers the HLD's open question: "Which preferences are remembered, and whether they are learned or asked". `future-scope.md` defers a `preferences` state slice to this decision.
- Candidate contents: usual countries and places, currency, roles and title variants that worked, rejected titles, seniority, `focus` choices, preferred sources, answers to Clarifying Questions that keep repeating, and resume facts if [What a Resume is for](17-what-a-resume-is-for.md) says the resume feeds the profile. For each one, decide whether it's kept and why.
- How it's learned: by code from finished Runs' state (counts and recency), by an LLM summary, or both. When it updates (on `Done`? on a Pause answer?). How old Runs fade.
- Where it lives: a per-user namespace in the LangGraph Store (the HLD's plan) or a plain table. Load `langchain-router` first for the Store.
- What the user can see, edit and clear, and whether a Run can opt out.
- The new glossary term (User Profile), and how it differs from an Assumption.
