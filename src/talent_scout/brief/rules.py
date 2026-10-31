from talent_scout.brief.types import BriefDraft, Confidence, HiringOutlook, Insight, InsightDraft, OutlookRating
from talent_scout.kernel.state import LogKind, RunLogEntry
from talent_scout.kernel.text import employer_key
from talent_scout.kernel.types import Evidence, HiringRequest, MarketStats, Posting, Source

SOURCE_NAMES = {Source.adzuna: "Adzuna", Source.usajobs: "USAJOBS"}

THIN_SAMPLE = 10  # below it no Stat rates above Low, so no Dimension is filled
HIGH_STAT, MEDIUM_STAT = (30, 10), (10, 5)  # Postings, employers
OLD_DAYS = 30
MIN_OUTLOOK_POSTINGS = 20  # the lowest target a Search Plan can have

_WEAKEST_FIRST = (Confidence.low, Confidence.medium, Confidence.high)


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


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


def rule_draft(stats: MarketStats) -> BriefDraft:
    summary = f"The Sample holds {plural(stats.sample_size, 'Posting')}. The Insights below state computed figures directly."
    # With nothing written yet, every Dimension with Stats counts as a gap.
    return BriefDraft(summary=summary, summary_stat_ids=["demand.sample_size"], insights=fill_gaps(stats, []))


def _rate(postings: int, employers: int, exempt: bool) -> Confidence:
    for (min_postings, min_employers), rating in ((HIGH_STAT, Confidence.high), (MEDIUM_STAT, Confidence.medium)):
        if postings >= min_postings and (exempt or employers >= min_employers):
            return rating
    return Confidence.low


def _tag(draft: InsightDraft, stats: MarketStats, by_key: dict[str, Posting], supported: bool | None) -> Insight:
    by_id = {s.id: s for s in stats.stats}
    cited = [by_id[i] for i in draft.stat_ids]

    # The Insight is only as strong as its thinnest cited Stat. An employer's own count covers one employer by construction.
    rated = []
    for stat in cited:
        keys = stat.evidence.posting_keys
        employers = len({employer_key(by_key[k].company) or k for k in keys})
        rating = _rate(len(keys), employers, stat.id.startswith("competition.employer."))
        rated.append((_WEAKEST_FIRST.index(rating), len(keys), employers))
    rank, postings, employers = min(rated)

    caps = []
    if any(s.id.startswith("comp.estimated.") for s in cited):
        caps.append("pay is estimated")
    if any(s.id.startswith("skills.") for s in cited) and any(p.source == Source.adzuna for p in by_key.values()):
        caps.append("skills come from snippets")
    if (age := by_id.get("demand.median_age_days")) and age.value > OLD_DAYS:
        caps.append("data is old")
    if supported is False:  # no verdict is not a failed one
        caps.append("the critic couldn't confirm it")

    rating = _WEAKEST_FIRST[min(rank, 1) if caps else rank]
    reason = f"{rating.value.capitalize()}: weakest cited Stat has {plural(postings, 'Posting')} from {plural(employers, 'employer')}"
    return Insight(
        text=draft.text, dimension=cited[0].dimension, stat_ids=draft.stat_ids,
        evidence=Evidence(posting_keys=[k for s in cited for k in s.evidence.posting_keys]),
        confidence=rating, confidence_reason="".join([reason, *(f"; {c}" for c in caps)]),
    )


def build_insights(stats: MarketStats, sample: list[Posting], drafts: list[InsightDraft], verdicts: list[bool]) -> list[Insight]:
    """Tags the writer's Insights then the gap fills. `verdicts` line up with `drafts` by position, and fills are never judged."""
    by_key = {p.key: p for p in sample}
    everything = [*drafts, *fill_gaps(stats, drafts)]
    return [_tag(d, stats, by_key, verdicts[i] if i < len(verdicts) else None) for i, d in enumerate(everything)]


def default_outlook(sample_size: int) -> HiringOutlook:
    if sample_size >= MIN_OUTLOOK_POSTINGS:
        # Stand-in until the outlook rules land: the Sample is big enough, so "too few" would be false.
        reason = "The Hiring Outlook is not rated yet, so Competitive is a placeholder rather than a finding."
    else:
        reason = f"Only {sample_size} Postings, too few to judge the talent market, so Competitive is a default rather than a finding."
    return HiringOutlook(rating=OutlookRating.competitive, reason=reason, stat_ids=[], evidence=Evidence(posting_keys=[]))


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
