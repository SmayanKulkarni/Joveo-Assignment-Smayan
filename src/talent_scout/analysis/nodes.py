import re
from collections import Counter

from langgraph.types import Send

from talent_scout.analysis.prompts import EXTRACT_SYSTEM, MERGE_SYSTEM
from talent_scout.analysis.stats import compute_stats, fold, mentions
from talent_scout.analysis.types import BatchFacts, ExtractBatch, Extraction, PostingFacts, SkillGroup, SkillGroups
from talent_scout.kernel.llm import LLMExhausted
from talent_scout.kernel.state import LogKind, RunLogEntry, State, log
from talent_scout.kernel.types import Posting
from talent_scout.runtime.deps import Deps, Node, Router

MAX_BATCH_POSTINGS = 20
MAX_BATCH_CHARS = 20_000
EXTRACT_MAX_TOKENS = 8192  # the cheap tier's default 2,048 fails on 10 Postings
MAX_YEARS = 40
MERGE_MAX_TOKENS = 8192
MAX_SKILLS_TO_MERGE = 300  # only 15 are reported, so the tail can't reach them


def _batches(postings: list[Posting]) -> list[list[Posting]]:
    # Sorted so the same Sample gives byte-identical prompts, which the replay cache needs.
    batches, chars = [[]], 0
    for p in sorted(postings, key=lambda p: p.key):
        if batches[-1] and (len(batches[-1]) == MAX_BATCH_POSTINGS or chars + len(p.description) > MAX_BATCH_CHARS):
            batches, chars = [*batches, []], 0
        batches[-1].append(p)
        chars += len(p.description)
    return batches


def fan_out(state: State) -> str | list[Send]:
    if not state.sample:
        return "stats"
    return [Send("batch_extract", ExtractBatch(postings=b)) for b in _batches(state.sample_postings)]


def _grounded(item: PostingFacts, p: Posting) -> Extraction:
    """Keeps only what the Posting's own text supports, so every number traces to real Postings."""
    text = f"{p.title} {p.description}"
    folded = fold(text)
    skills = [s for s in item.skills if mentions(fold(s.name), folded)]
    years = item.years_min
    if years is not None and not (years <= MAX_YEARS and re.search(rf"\b{years}\b", text)):
        years = None
    return Extraction(
        skills=skills, seniority=item.seniority, years_min=years, employer_type=item.employer_type,
        ungrounded=len(item.skills) - len(skills),
    )


def _text(postings: list[Posting]) -> str:
    blocks = []
    for ref, p in enumerate(postings):
        lines = [f"ref {ref}", f"title: {p.title}"]
        if p.company:
            lines.append(f"company: {p.company}")
        blocks.append("\n".join([*lines, f"description: {p.description}"]))
    return "\n\n".join(blocks)


def _names_to_merge(extractions: dict[str, Extraction]) -> list[str]:
    counts = Counter(fold(s.name) for e in extractions.values() for s in e.skills)
    # Ties break by name so the cut is the same whatever order the branches finished in.
    top = sorted(counts, key=lambda n: (-counts[n], n))[:MAX_SKILLS_TO_MERGE]
    return sorted(top)


def _aliases(groups: list[SkillGroup], names: set[str]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for g in groups:
        canonical = g.canonical.strip()
        if not fold(canonical):
            continue
        for variant in map(fold, g.variants):
            # Only names the model was shown can be aliased, and the first group to claim one keeps it.
            if variant in names and variant != fold(canonical):
                aliases.setdefault(variant, canonical)
    return aliases


def make_nodes(deps: Deps) -> dict[str, Node]:
    chain = deps.tiers.structured(
        "cheap", BatchFacts, system=EXTRACT_SYSTEM, name="batch_extract", max_tokens=EXTRACT_MAX_TOKENS
    )
    merge_chain = deps.tiers.structured(
        "cheap", SkillGroups, system=MERGE_SYSTEM, name="normalise_skills", max_tokens=MERGE_MAX_TOKENS
    )

    async def batch_extract(batch: ExtractBatch) -> dict:
        try:
            out = await chain.ainvoke(_text(batch.postings))
        except LLMExhausted as e:
            if not e.bad_output:
                raise
            return {}  # the same text would fail on every resume, so stats raises a Caveat instead
        found = {}
        for item in out.items:
            if 0 <= item.ref < len(batch.postings):
                p = batch.postings[item.ref]
                found.setdefault(p.key, _grounded(item, p))
        return {"extractions": found}

    async def normalise_skills(state: State) -> dict:
        names = _names_to_merge(state.extractions)
        if not names:
            return {"skill_aliases": {}, **log(state, "normalise_skills", LogKind.note, "No skills to merge")}
        try:
            out = await merge_chain.ainvoke("\n".join(names))
        except LLMExhausted as e:
            if not e.bad_output:
                raise
            # Folding alone still gives true counts, only more split.
            message = "Skills merged by spelling only: the model's grouping was unusable"
            return {"skill_aliases": {}, **log(state, "normalise_skills", LogKind.caveat, message)}
        aliases = _aliases(out.groups, set(names))
        # Every merge is listed so a reader of the run log can catch a bad one.
        merges = ", ".join(f"{variant} → {canonical}" for variant, canonical in aliases.items())
        message = f"Merged {len(aliases)} spellings: {merges}" if aliases else "No spellings merged"
        return {"skill_aliases": aliases, **log(state, "normalise_skills", LogKind.note, message, merged=len(aliases))}

    async def stats(state: State) -> dict:
        market, caveats, summary = compute_stats(state)
        entries = [RunLogEntry(node="stats", kind=LogKind.caveat, message=m, data={}) for m in caveats]
        note = (
            f"{summary['sample_size']} Postings, {summary['extracted']} extracted, {summary['stats']} Stats produced, "
            f"{summary['ungrounded']} skills dropped as ungrounded"
        )
        entries.append(RunLogEntry(node="stats", kind=LogKind.note, message=note, data=summary))
        return {"stats": market, "run_log": [*state.run_log, *entries]}

    return {"batch_extract": batch_extract, "normalise_skills": normalise_skills, "stats": stats}


ROUTERS: dict[str, Router] = {}
