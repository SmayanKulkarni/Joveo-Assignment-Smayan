from talent_scout.analysis.stats import mentions
from talent_scout.analysis.types import Extraction, Level, Match, MatchedSkill, Requirement, ResumeFacts, Seniority
from talent_scout.kernel.text import fold
from talent_scout.kernel.types import Posting

# Tuned on three fictional Resumes against recorded Postings; see tests/test_match.py.
WEIGHTS = {Requirement.must: 2.0, Requirement.unstated: 1.0, Requirement.nice: 0.5}
WEIGHT_FLOOR = 5  # stops a two-skill snippet scoring 100
MIN_MATCHED = 2
MIN_SCORE = 40
MAX_SHOWN = 20
YEARS_STRETCH = 2  # years short of the Posting's minimum that still count as a stretch
LADDER = [Seniority.entry, Seniority.mid, Seniority.senior, Seniority.lead, Seniority.executive]


_ORDER = [Level.fits, Level.stretch, Level.far]


def _canon(aliases: dict[str, str], name: str) -> str:
    folded = fold(name)
    return fold(aliases.get(folded, folded))


def _level(extraction: Extraction, resume: ResumeFacts) -> tuple[Level, str]:
    results: list[tuple[Level, str]] = []
    if extraction.seniority in LADDER and resume.seniority in LADDER:
        gap = LADDER.index(extraction.seniority) - LADDER.index(resume.seniority)
        level = Level.fits if -1 <= gap <= 0 else Level.stretch if gap == 1 else Level.far
        results.append((level, f"the Posting is {extraction.seniority.value} and the Resume {resume.seniority.value}"))
    if extraction.years_min is not None and resume.years is not None:
        short = extraction.years_min - resume.years
        level = Level.fits if short <= 0 else Level.stretch if short <= YEARS_STRETCH else Level.far
        results.append((level, f"the Posting asks for {extraction.years_min} years and the Resume has {resume.years}"))
    if not results:
        return Level.not_judged, "neither side states enough to compare"
    return max(results, key=lambda r: _ORDER.index(r[0]))


def score_posting(key: str, extraction: Extraction, resume: ResumeFacts, aliases: dict[str, str]) -> Match:
    have = {_canon(aliases, s.name): s for s in resume.skills}
    matched, missing, got, total = [], [], 0.0, 0.0
    for skill in extraction.skills:
        weight = WEIGHTS[skill.requirement]
        total += weight
        wanted = _canon(aliases, skill.name)
        # Only this direction counts: asking for SQL is met by SQL Server, asking for SQL Server is not met by SQL.
        owned = have.get(wanted) or next((s for name, s in have.items() if mentions(wanted, name)), None)
        if owned:
            got += weight
            matched.append(MatchedSkill(posting=skill.name, resume=owned.name, added=owned.added))
        else:
            missing.append(skill.name)
    level, reason = _level(extraction, resume)
    return Match(
        posting_key=key, score=round(100 * got / max(total, WEIGHT_FLOOR)), matched=matched, missing=missing,
        level=level, level_reason=reason,
    )


def rank(matches: list[Match], postings: dict[str, Posting]) -> list[Match]:
    # Far goes after everything else, then the higher score, more matched skills, the newer Posting, and the key.
    return sorted(
        matches,
        key=lambda m: (m.level == Level.far, -m.score, -len(m.matched), -postings[m.posting_key].posted_at.toordinal(), m.posting_key),
    )


def default_view(ranked: list[Match]) -> list[Match]:
    return [m for m in ranked if len(m.matched) >= MIN_MATCHED and m.score >= MIN_SCORE][:MAX_SHOWN]


def compute_matches(
    resume: ResumeFacts, sample: list[Posting], extractions: dict[str, Extraction], aliases: dict[str, str]
) -> tuple[list[Match], int]:
    """Ranked Matches for every extracted Posting, and how many had no Extraction to score."""
    scored = [score_posting(p.key, extractions[p.key], resume, aliases) for p in sample if p.key in extractions]
    return rank(scored, {p.key: p for p in sample}), len(sample) - len(scored)
