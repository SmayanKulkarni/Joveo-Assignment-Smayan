# Assemble docs/HLD.md

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by: 16

## Question

Write `docs/HLD.md` from the resolved tickets: system context, component list and boundaries, graph diagram, concept-level state ownership, Pauses and durable resume, Jev placements, data gateway, infra topology (future phase), build order. Gist and link each decision to its ticket; do not introduce new decisions.

## Answer

Done: [docs/HLD.md](../../../docs/HLD.md). Twelve sections, each gisting and linking its source tickets; no new decisions. The infra topology diagram only shows what tickets 02, 04, 09 and 10 already decided (shell wraps the Run Controller; sweep becomes a scheduled job; SQLite replaced). Queue technology and the other infra internals are explicitly left to the infra shell's LLD.
