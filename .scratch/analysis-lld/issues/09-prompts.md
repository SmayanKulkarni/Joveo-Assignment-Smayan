# Prompts

Type: grilling (delegated to the agent)
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01, 02, 05

## Question

What must each Analysis prompt get and do?

## Answer

As in Collection and Request & Plan: the LLD fixes inputs and rules, the wording lives in `analysis/prompts.py`, and it's tuned on real runs. The write-up reports what changed.

The probe gives the build a tested start, and the write-up a real "what I changed after testing" story. Both of these changes came from reading its output:

- **`EXTRACT_SYSTEM`:** went from "each concrete skill" to "things a person could list on a CV, one to four words, copied exactly, one per entry, split lists, leave out duties and the role's own name". The top entries went from "data engineering" and "pipelines" to named tools. Still imperfect: "fraud detection" and "cancer research" get through, which ranking by employer handles.
- **`MERGE_SYSTEM`:** went from "mean exactly the same skill" to a definition of a variant (usable in place of the canonical name in any sentence), named things that stay apart, and "if unsure, leave it out". Over-merges went from at least 5 clear cases to none in 12.

Both treat Posting text as data, never instructions, since job ads come from third parties and reach the model verbatim.

Stable text comes first, as `Tiers.structured` already enforces (Kernel §12), so Batches share a cached prefix.
