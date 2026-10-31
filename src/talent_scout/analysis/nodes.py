import re

from langgraph.types import Send

from talent_scout.analysis.prompts import EXTRACT_SYSTEM
from talent_scout.analysis.types import BatchFacts, ExtractBatch, Extraction, PostingFacts
from talent_scout.kernel.llm import LLMExhausted
from talent_scout.kernel.state import State
from talent_scout.kernel.types import Posting
from talent_scout.runtime.deps import Deps, Node, Router

MAX_BATCH_POSTINGS = 20
MAX_BATCH_CHARS = 20_000
EXTRACT_MAX_TOKENS = 8192  # the cheap tier's default 2,048 fails on 10 Postings
MAX_YEARS = 40


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


def fold(s: str) -> str:
    # Keeps + and # so C, C++ and C# stay three skills.
    return " ".join(re.sub(r"[^\w+#]+", " ", s.casefold()).split())


def _mentions(term: str, text: str) -> bool:
    # An empty term would match between any two words.
    return bool(term) and re.search(rf"(?<![\w+#]){re.escape(term)}(?![\w+#])", text) is not None


def _grounded(item: PostingFacts, p: Posting) -> Extraction:
    """Keeps only what the Posting's own text supports, so every number traces to real Postings."""
    text = f"{p.title} {p.description}"
    folded = fold(text)
    skills = [s for s in item.skills if _mentions(fold(s.name), folded)]
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


def make_nodes(deps: Deps) -> dict[str, Node]:
    chain = deps.tiers.structured(
        "cheap", BatchFacts, system=EXTRACT_SYSTEM, name="batch_extract", max_tokens=EXTRACT_MAX_TOKENS
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

    return {"batch_extract": batch_extract}


ROUTERS: dict[str, Router] = {}
