import re

from pydantic import model_validator

from talent_scout.brief.types import (
    BandRecommendation, BriefDraft, BriefRevision, ClientRecommendations, Confidence, HiringOutlook, Insight, InsightDraft, OutlookRating,
    SkillsRecommendation, TitleRecommendation,
)
from talent_scout.kernel.state import LogKind, RunLogEntry
from talent_scout.kernel.text import employer_key, plural
from talent_scout.kernel.types import Evidence, HiringRequest, MarketStats, Posting, Source, Stat

SOURCE_NAMES = {Source.adzuna: "Adzuna", Source.usajobs: "USAJOBS"}

MAX_INSIGHTS, THIN_MAX_INSIGHTS = 8, 3
THIN_SAMPLE = 10  # below it no Stat rates above Low, so no Dimension is filled
HIGH_STAT, MEDIUM_STAT = (30, 10), (10, 5)  # Postings, employers
OLD_DAYS = 30
MIN_OUTLOOK_POSTINGS = 20  # the lowest target a Search Plan can have
MANY_EMPLOYERS, FEW_EMPLOYERS = 20, 10
HIGH_BAR_YEARS, HIGH_BAR_SENIOR_SHARE = 5, 0.5
MIN_TITLE_POSTINGS, MIN_TITLE_EMPLOYERS = 3, 2
TOP_SKILLS, MIN_SKILL_EMPLOYERS = 5, 3

# First match wins, in this order. The levels are the same strings as Analysis's Seniority.
LEVEL_WORDS = {
    "entry": {"junior", "entry", "graduate", "intern"},
    "mid": {"mid"},
    "senior": {"senior", "sr"},
    "lead": {"lead", "principal", "staff"},
    "executive": {"director", "head", "vp", "chief", "executive"},
}
HIGH_LEVELS = ("senior", "lead", "executive")
PROXY = "Postings show demand, not candidates, so this is an estimate of the talent market."

_WEAKEST_FIRST = (Confidence.low, Confidence.medium, Confidence.high)


def empty_draft(request: HiringRequest) -> BriefDraft:
    summary = f"No Relevant Postings were found for {request.role} in {request.location}, so this Brief has no market findings."
    return BriefDraft(summary=summary, summary_stat_ids=[], insights=[])


def fill_gaps(stats: MarketStats, insights: list[InsightDraft]) -> list[InsightDraft]:
    """One Stat-label Insight for each Dimension that no Insight cites, as the writer's drafts never fully cover them."""
    if stats.sample_size < THIN_SAMPLE and insights:
        return []
    by_id = {s.id: s for s in stats.stats}
    covered = {by_id[i].dimension for d in insights for i in d.stat_ids}
    first = {}
    for stat in stats.stats:
        first.setdefault(stat.dimension, stat)
    return [InsightDraft(text=s.label, stat_ids=[s.id]) for dimension, s in first.items() if dimension not in covered]


def insight_cap(sample_size: int) -> int:
    return THIN_MAX_INSIGHTS if sample_size < THIN_SAMPLE else MAX_INSIGHTS


def rule_draft(stats: MarketStats) -> BriefDraft:
    summary = f"The Sample holds {plural(stats.sample_size, 'Posting')}. The Insights below state computed figures directly."
    # With nothing written yet, every Dimension with Stats counts as a gap, up to the cap for a thin Sample.
    insights = fill_gaps(stats, [])[:insight_cap(stats.sample_size)]
    return BriefDraft(summary=summary, summary_stat_ids=["demand.sample_size"], insights=insights)


def fmt_value(value: float | str) -> str:
    """A whole number gets commas and no ".0", as raw values gave "125.0 Postings" in the writer's text."""
    return value if isinstance(value, str) else format(value, ",.10g")


# `S3` isn't a number, and `$134k` is 134,000.
_NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?[kKmM]?(?!\w)")
_SCALE = {"k": 1_000, "m": 1_000_000}


def _figures(text: str) -> set[float]:
    found = set()
    for raw in _NUMBER.findall(text):
        scale = _SCALE.get(raw[-1].lower(), 1)
        found.add(float(raw.rstrip("kKmM").replace(",", "")) * scale)
    return found


def _allowed_figures(stats: MarketStats, known_text: str) -> set[float]:
    text = " ".join([known_text, *(f"{s.label} {fmt_value(s.value)}" for s in stats.stats)])
    allowed = _figures(text)
    # Each also as a whole number, so 38% matches 38.4%.
    return allowed | {float(round(n)) for n in allowed}


def _problems(what: str, text: str, stat_ids: list[str], known: set[str], allowed: set[float]) -> list[str]:
    problems = []
    if not text.strip():
        problems.append(f"{what} is blank")
    if not stat_ids:
        problems.append(f"{what} cites no Stat ids")
    elif unknown := [i for i in stat_ids if i not in known]:
        problems.append(f"{what} cites unknown Stat ids: {', '.join(unknown)}")
    # Only inventions are caught here. A figure from a Stat it didn't cite is for the critic.
    if invented := sorted(_figures(text) - allowed):
        problems.append(f"{what} states figures found in no Stat, Caveat or the request: {', '.join(f'{n:g}' for n in invented)}")
    return problems


def _insight_problems(insights: list[InsightDraft], cap: int, known: set[str], allowed: set[float]) -> list[str]:
    problems = [f"There are {len(insights)} Insights, over the maximum of {cap}"] if len(insights) > cap else []
    for n, insight in enumerate(insights, 1):
        problems += _problems(f"Insight {n}", insight.text, insight.stat_ids, known, allowed)
    return problems


def checked_draft(stats: MarketStats, known_text: str, cap: int) -> type[BriefDraft]:
    """BriefDraft with this Run's checks, so Kernel's feedback retry makes the model fix a bad reply and the limits stay out of the schema."""
    known, allowed = {s.id for s in stats.stats}, _allowed_figures(stats, known_text)

    class CheckedDraft(BriefDraft):
        @model_validator(mode="after")
        def _check(self):
            problems = _problems("Summary", self.summary, self.summary_stat_ids, known, allowed)
            if not self.insights:
                problems.append("There are no Insights")
            problems += _insight_problems(self.insights, cap, known, allowed)
            if problems:
                raise ValueError("; ".join(problems))
            return self

    return CheckedDraft


def checked_revision(stats: MarketStats, known_text: str, cap: int, kept_texts: list[str]) -> type[BriefRevision]:
    """The same checks on a revision, where `cap` is what the kept Insights leave. No replacements is valid: those claims are dropped."""
    known, allowed = {s.id for s in stats.stats}, _allowed_figures(stats, known_text)
    kept = {t.strip().casefold() for t in kept_texts}

    class CheckedRevision(BriefRevision):
        @model_validator(mode="after")
        def _check(self):
            problems = _insight_problems(self.insights, cap, known, allowed)
            # A reworded copy of a kept finding would ship it twice.
            problems += [f"Insight {n} repeats an Insight that is kept" for n, i in enumerate(self.insights, 1) if i.text.strip().casefold() in kept]
            if problems:
                raise ValueError("; ".join(problems))
            return self

    return CheckedRevision


def _rate(postings: int, employers: int, exempt: bool) -> Confidence:
    for (min_postings, min_employers), rating in ((HIGH_STAT, Confidence.high), (MEDIUM_STAT, Confidence.medium)):
        if postings >= min_postings and (exempt or employers >= min_employers):
            return rating
    return Confidence.low


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.casefold()))


def _employers(keys: list[str], by_key: dict[str, Posting]) -> int:
    # A Posting with no company counts as its own employer.
    return len({employer_key(by_key[k].company) or k for k in keys})


def _union(stats: list[Stat]) -> Evidence:
    return Evidence(posting_keys=[k for s in stats for k in s.evidence.posting_keys])


def _tag(draft: InsightDraft, by_id: dict[str, Stat], by_key: dict[str, Posting], has_adzuna: bool, supported: bool | None) -> Insight:
    cited = [by_id[i] for i in draft.stat_ids]

    # The Insight is only as strong as its thinnest cited Stat. An employer's own count covers one employer by construction.
    rated = []
    for stat in cited:
        keys = stat.evidence.posting_keys
        employers = _employers(keys, by_key)
        rating = _rate(len(keys), employers, stat.id.startswith("competition.employer."))
        rated.append((_WEAKEST_FIRST.index(rating), len(keys), employers))
    rank, postings, employers = min(rated)

    caps = []
    if any(s.id.startswith("comp.estimated.") for s in cited):
        caps.append("pay is estimated")
    if any(s.id.startswith("skills.") for s in cited) and has_adzuna:
        caps.append("skills come from snippets")
    if (age := by_id.get("demand.median_age_days")) and age.value > OLD_DAYS:
        caps.append("data is old")
    if supported is False:  # no verdict is not a failed one
        caps.append("the critic couldn't confirm it")

    rating = _WEAKEST_FIRST[min(rank, 1) if caps else rank]
    reason = f"{rating.value.capitalize()}: weakest cited Stat has {plural(postings, 'Posting')} from {plural(employers, 'employer')}"
    return Insight(
        text=draft.text, dimension=cited[0].dimension, stat_ids=draft.stat_ids,
        evidence=_union(cited), confidence=rating, confidence_reason="".join([reason, *(f"; {c}" for c in caps)]),
    )


def build_insights(stats: MarketStats, sample: list[Posting], drafts: list[InsightDraft], verdicts: list[bool]) -> list[Insight]:
    """Tags the writer's Insights then the gap fills. `verdicts` line up with `drafts` by position, and fills are never judged."""
    by_id, by_key = {s.id: s for s in stats.stats}, {p.key: p for p in sample}
    has_adzuna = any(p.source == Source.adzuna for p in sample)
    everything = [*drafts, *fill_gaps(stats, drafts)]
    return [_tag(d, by_id, by_key, has_adzuna, verdicts[i] if i < len(verdicts) else None) for i, d in enumerate(everything)]


def request_level(request: HiringRequest) -> str | None:
    words = _words(request.seniority or "")
    return next((level for level, names in LEVEL_WORDS.items() if words & names), None)


def outlook(stats: MarketStats, request: HiringRequest) -> HiringOutlook:
    n = stats.sample_size
    if n < MIN_OUTLOOK_POSTINGS:
        reason = f"Only {plural(n, 'Posting')}, too few to judge the talent market, so Competitive is a default rather than a finding. {PROXY}"
        return HiringOutlook(rating=OutlookRating.competitive, reason=reason, stat_ids=[], evidence=Evidence(posting_keys=[]))

    by_id = {s.id: s for s in stats.stats}
    employers, years, trend = by_id.get("competition.distinct_employers"), by_id.get("skills.years_median"), by_id.get("demand.trend")
    seniority = [s for s in stats.stats if s.id.startswith("seniority.")]
    level = request_level(request)
    senior_share = sum(s.value for s in seniority if s.id.rsplit(".", 1)[1] in HIGH_LEVELS)

    high_bar = level in HIGH_LEVELS or (years is not None and years.value >= HIGH_BAR_YEARS) or senior_share >= HIGH_BAR_SENIOR_SHARE
    known_bar = level is not None or years is not None or bool(seniority)
    count = int(employers.value) if employers else None
    direction = trend.value if trend else None

    # The trend only blocks: Analysis says it tilts recent, so it can't rate anything by itself.
    if count is not None and count >= MANY_EMPLOYERS and high_bar and direction != "falling":
        rating = OutlookRating.hard_to_fill
    elif count is not None and count < FEW_EMPLOYERS and known_bar and not high_bar and direction != "rising":
        rating = OutlookRating.favourable
    else:
        rating = OutlookRating.competitive

    lead = f"{plural(count, 'employer')} across {plural(n, 'Posting')}" if count is not None else f"No employers named across {plural(n, 'Posting')}"
    facts = [
        *([f"{'an' if level[0] in 'aeiou' else 'a'} {level} level requested"] if level else []),
        *([f"a median of {years.value:g} years asked"] if years else []),
        *([f"{senior_share:.0%} of extracted Postings at senior level or above"] if seniority else []),
        *([f"a {direction} trend"] if trend else []),
    ]
    reason = f"{lead}{', with ' + ', '.join(facts) if facts else ''}. {PROXY}"
    consulted = [s for s in (employers, years, *seniority, trend) if s]
    return HiringOutlook(rating=rating, reason=reason, stat_ids=[s.id for s in consulted], evidence=_union(consulted))


def _name(stat: Stat) -> str:
    # Stat has no name field, so the name is the label before its last ": ".
    return stat.label.rsplit(": ", 1)[0]


def _title(stats: MarketStats, by_key: dict[str, Posting], level: str | None) -> TitleRecommendation | None:
    level_words = LEVEL_WORDS.get(level, set())
    candidates = []
    for s in stats.stats:
        if not s.id.startswith("titles.variant."):
            continue
        postings, employers = s.evidence.count, _employers(s.evidence.posting_keys, by_key)
        if postings >= MIN_TITLE_POSTINGS and employers >= MIN_TITLE_EMPLOYERS:
            has_level = bool(level_words & _words(_name(s)))
            candidates.append(((not has_level, -employers, -postings, s.id), s, postings, employers, has_level))
    if not candidates:
        return None
    _, stat, postings, employers, has_level = min(candidates, key=lambda c: c[0])
    reason = f"Used in {plural(postings, 'Posting')} from {plural(employers, 'employer')}"
    if has_level:
        reason += f", and it names the {level} level requested"
    return TitleRecommendation(title=_name(stat), reason=f"{reason}.", stat_ids=[stat.id], evidence=stat.evidence)


_PAY_WORDING = {"advertised": "advertised", "estimated": "Adzuna-estimated", "federal": "federal"}
_PAY_NOTE = {
    "estimated": " These are Adzuna's estimates, not pay employers stated.",
    "federal": " Federal pay follows fixed tables.",
}


def _band(by_id: dict[str, Stat], sample: list[Posting], level: str | None) -> BandRecommendation | None:
    # Federal pay only counts as a market signal when most of the Sample is federal.
    mostly_federal = sum(p.source == Source.usajobs for p in sample) * 2 > len(sample)
    for group in ("advertised", "estimated", *(("federal",) if mostly_federal else ())):
        # The request's level slice if the group has one, otherwise the whole group.
        scopes = [(f"comp.{group}.{level}", f"at {level} level")] if level else []
        for prefix, scope in [*scopes, (f"comp.{group}", "at all levels")]:
            cited = [by_id.get(f"{prefix}.{part}") for part in ("p25", "median", "p75")]
            if all(cited):
                p25, median, p75 = cited
                reason = f"Middle 50% of {plural(median.evidence.count, _PAY_WORDING[group] + ' figure')}, {scope}.{_PAY_NOTE.get(group, '')}"
                return BandRecommendation(
                    low=float(p25.value), high=float(p75.value), unit=p25.unit, reason=reason,
                    stat_ids=[s.id for s in cited], evidence=_union(cited),
                )
    return None


def _skills(stats: MarketStats, by_key: dict[str, Posting], has_adzuna: bool) -> SkillsRecommendation | None:
    counts = [
        s for s in stats.stats
        if s.id.startswith("skills.") and s.id.endswith(".count") and _employers(s.evidence.posting_keys, by_key) >= MIN_SKILL_EMPLOYERS
    ][:TOP_SKILLS]  # Stat order is already by employers
    if not counts:
        return None
    listing = ", ".join(f"{_name(s)} ({plural(s.evidence.count, 'Posting')})" for s in counts)
    reason = f"Asked for by the most employers: {listing}." + (" Skills come from Adzuna snippets, so counts are partial." if has_adzuna else "")
    return SkillsRecommendation(skills=[_name(s) for s in counts], reason=reason, stat_ids=[s.id for s in counts], evidence=_union(counts))


def recommendations(stats: MarketStats, request: HiringRequest, sample: list[Posting]) -> ClientRecommendations:
    by_id, by_key = {s.id: s for s in stats.stats}, {p.key: p for p in sample}
    level = request_level(request)
    return ClientRecommendations(
        job_title=_title(stats, by_key, level),
        salary_band=_band(by_id, sample, level),
        top_skills=_skills(stats, by_key, any(p.source == Source.adzuna for p in sample)),
    )


def match_totals(run_log: list[RunLogEntry]) -> list[str]:
    # The last collect note wins: it covers the final Attempt, and each total is the source's own count.
    notes = [e for e in run_log if e.node == "collect" and e.kind == LogKind.note and "totals" in e.data]
    if not notes:
        return []
    return [
        f"{SOURCE_NAMES[Source(source)]} reported about {total:,} matches for {title}. This is its own count, not a measure of demand."
        for title, by_source in notes[-1].data["totals"].items()
        for source, total in by_source.items()
    ]
