# What a Customer Profile holds

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: [Runs that belong to a Customer](15-runs-that-belong-to-a-customer.md), [What a Resume is for](17-what-a-resume-is-for.md)

## Question

What does a Customer Profile contain, how is it learned from a Customer's earlier Runs (and resume), and how does the CSM see and correct it? It holds the Customer's preferences, never the CSM's.

- This is the HLD's Long-term memory component (I), and it answers the HLD's open question: "Which preferences are remembered, and whether they are learned or asked". `future-scope.md` defers a `preferences` state slice to this decision.
- Candidate contents: usual countries and places, currency, roles and title variants that worked, rejected titles, seniority, `focus` choices, preferred sources, answers to Clarifying Questions that keep repeating, and resume facts if [What a Resume is for](17-what-a-resume-is-for.md) says the resume feeds the profile. For each one, decide whether it's kept and why.
- How it's learned: by code from finished Runs' state (counts and recency), by an LLM summary, or both. When it updates (on `Done`? on a Pause answer?). How old Runs fade.
- Whether a Customer's findings and Assumptions are read back from their finished Runs or copied into the profile. Finished Runs are pruned to their final state, so check that keeps everything needed.
- Where it lives: a per-Customer namespace in the LangGraph Store (the HLD's plan) or a plain table. Load `langchain-router` first for the Store.
- Sensitive traits such as health, religion, ethnicity, union membership, orientation, age or gender are never learned. Say what enforces that.
- What the CSM can see, edit and clear, and whether a Run can opt out.
- The new glossary term (Customer Profile), and how it differs from an Assumption.

## Answer

Decided by the agent alone on 2026-11-02, at the user's request, with no grilling. The decisions are in [Final decisions](../final-decisions.md#what-a-customer-profile-holds).
