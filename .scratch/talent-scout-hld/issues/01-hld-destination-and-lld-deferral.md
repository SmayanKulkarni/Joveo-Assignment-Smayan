# What does the HLD cover, and what is deferred to LLD?

Type: grilling
Status: resolved

## Question

What is the end state of this map, and where is the line between HLD (decided here) and LLD (decided later, per component)?

## Answer

Resolved during charting.

- Destination: `docs/HLD.md` plus an ordered component breakdown.
- HLD covers: system context, components with responsibilities and boundaries, node-level graph shape (nodes, edges, Pauses, loops), concept-level state ownership, infra topology, where Jev sits, build order.
- Deferred to one LLD/build effort per component: exact state fields and types, prompt text, retry counts and limits, thresholds, library and model picks.
- Supervisor multi-agent stretch goal is out of scope for now (may be revisited later).
