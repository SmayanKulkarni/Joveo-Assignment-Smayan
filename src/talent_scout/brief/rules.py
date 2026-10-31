from talent_scout.brief.types import BriefDraft, HiringOutlook, OutlookRating
from talent_scout.kernel.state import LogKind, RunLogEntry
from talent_scout.kernel.types import Evidence, HiringRequest, Source

SOURCE_NAMES = {Source.adzuna: "Adzuna", Source.usajobs: "USAJOBS"}


def empty_draft(request: HiringRequest) -> BriefDraft:
    summary = f"No Relevant Postings were found for {request.role} in {request.location}, so this Brief has no market findings."
    return BriefDraft(summary=summary, summary_stat_ids=[], insights=[])


def default_outlook(sample_size: int) -> HiringOutlook:
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
