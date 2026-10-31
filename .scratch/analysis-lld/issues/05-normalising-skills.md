# Normalising skills

Type: grilling (delegated to the agent)
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01, 02

## Question

"Postgres" and "PostgreSQL" must count once, across parallel Batches that can't see each other. Where does that happen, and how is over-merging prevented?

## Answer

**A new LLM node, `normalise_skills`, between the fan-in and `stats`,** on the cheap tier.

- **Why not inside each Batch:** Batches would choose different canonical names, and verbatim names are what make grounding possible.
- **Why not code alone:** synonyms like K8s and Kubernetes can't be computed, and an alias table only covers the roles it was written for. This agent takes any role.
- **Why not inside `stats`:** `stats` stays pure Python, per HLD §5, so it's deterministic and cheap to test.

**Steps**

1. Code folds every name and counts them. Case, spacing and punctuation variants merge here with no LLM.
2. The top `MAX_SKILLS_TO_MERGE = 300` folded names go to the model, sorted, so the prompt is stable for replay. Only 15 skills are reported, and a name outside the top 300 can't plausibly reach them. No names, no call.
3. The model returns only groups of two or more. Code keeps only variants that were in the input, and the first group wins if a name appears twice.
4. `skill_aliases: dict[str, str]` maps folded name → canonical name. A name absent from it stands for itself, displayed in its most common spelling.

**Over-merging is the failure that matters,** because an inflated count is a wrong number in a client Brief, while a split one only ranks a skill lower. The probe showed the prompt decides this: the loose wording merged `S3` into `AWS`, and the tight wording made 12 merges, all correct. So the prompt defines a variant, names what stays apart, and defaults to leaving a name out.

**No Jev veto.** It was tested as a check on each merge, and it agreed with all 12, so on this evidence it would add a fourth placement, a threshold and up to hundreds of calls to catch nothing. It's in `future-scope.md`, for if over-merging shows up in live runs. Note that it was never tried against a bad merge, so its veto power is unmeasured.

**Every merge goes in a run log `note`,** so a reader of the run log or a `samples/` transcript can see "Spark → Apache Spark" and catch a bad one. The live smoke asserts that known traps stay apart.

The fan-in means one `normalise_skills` per Run. `fan_out`'s zero-Postings path goes straight to `stats`, so `skill_aliases` stays empty there.
