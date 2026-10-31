# 02: Skill spellings merge into canonical names

**What to build:** after the fan-in, a real `normalise_skills` node groups spellings of the same skill into `skill_aliases` and lists every merge in the Run log, so a reader can catch a bad one. When the model gives bad output, folding alone still gives true counts, and a Caveat says so. Spec: [Analysis LLD](../../../docs/lld/analysis.md) §7, §10, §11, §13 step 5.

**Blocked by:** 01: Postings become grounded Extractions.

**Status:** done

- [x] Uses `tiers.structured("cheap", SkillGroups, system=MERGE_SYSTEM, name="normalise_skills", max_tokens=MERGE_MAX_TOKENS)`
- [x] Folds every skill name across `extractions`, counts them, and sends the top `MAX_SKILLS_TO_MERGE` as sorted lines
- [x] Writes each variant's folded name → `canonical`, for variants in the input only, and the first group wins when a name repeats
- [x] A variant equal to its canonical name is skipped
- [x] A `note` lists every merge, like "Spark → Apache Spark"
- [x] `MERGE_SYSTEM` in `prompts.py` follows every §11 rule, starting from the probed wording in the Prompts design ticket
- [x] Transient `LLMExhausted` propagates
- [x] Test: no names means no call, and it writes `{}` plus its log entry
- [x] Test: a variant not in the input is ignored, and the first group wins
- [x] Test: the merge `note` is written
- [x] Test: bad output leaves aliases empty and raises the "Skills merged by spelling only" Caveat, and good output doesn't raise it
