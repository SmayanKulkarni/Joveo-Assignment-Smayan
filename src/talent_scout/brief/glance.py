import re
from collections import Counter

from talent_scout.brief.rules import _employers, _name
from talent_scout.brief.types import MarketBrief
from talent_scout.kernel.types import Evidence, Model, Posting, Stat

MAX_NOTES = 2
SKILL_ROWS, PLACE_ROWS, EMPLOYER_ROWS = 8, 6, 5
MIN_SKILL_EMPLOYERS = 2  # a skill one employer wrote into every ad says nothing about the market
NO_AREA = "Area not given"


class Row(Model):
    label: str
    count: int
    required: int | None = None  # skills only: how many of `count` call it required
    stat_ids: list[str]
    evidence: Evidence


class RowChart(Model):
    caption: str
    rows: list[Row]


class PayChart(Model):
    low: float
    median: float
    high: float
    unit: str
    postings: int
    stat_ids: list[str]
    evidence: Evidence


class Glance(Model):
    reader_notes: list[str]
    pay: PayChart | None
    skills: RowChart | None
    places: RowChart | None
    employers: RowChart | None


def _caveat_tail(caveats: list[str], prefix: str) -> str | None:
    return next((c.removeprefix(prefix).strip() for c in caveats if c.startswith(prefix)), None)


def _reader_notes(brief: MarketBrief) -> list[str]:
    notes, stats = brief.run_notes, brief.stats
    caveats = notes.caveats
    first = notes.earlier_plans[0] if notes.earlier_plans else notes.final_plan
    missed = _caveat_tail(caveats, "Places not searched:")
    target = notes.final_plan.target_postings
    # The first that apply, in the LLD's order, so a reader sees the few that change how far to trust the Brief.
    candidates = [
        (first.locations and not notes.final_plan.locations, f"We searched the whole country, not only {', '.join(first.locations)}."),
        (missed, f"We couldn't search {missed}."),
        (stats.sample_size < target, f"Only {stats.sample_size} postings against the {target} we aimed for, so treat this as a rough guide."),
        (notes.earlier_plans, "We widened the search to find enough postings."),
        (any(c.startswith("Old data") for c in caveats), "Most of these postings are over 30 days old."),
        (any(c.startswith("Mostly federal") for c in caveats), "Most of these postings are US federal jobs."),
        (any(c.startswith("One source failed") for c in caveats), "One job source didn't answer, so this rests on the other."),
    ]
    return [text for applies, text in candidates if applies][:MAX_NOTES]


def _pay(brief: MarketBrief) -> PayChart | None:
    band = brief.recommendations.salary_band
    if not band:
        return None
    by_id = {s.id: s for s in brief.stats.stats}
    median = next((by_id[i] for i in band.stat_ids if i.endswith(".median") and i in by_id), None)
    if not median:
        return None
    return PayChart(
        low=band.low, median=float(median.value), high=band.high, unit=band.unit, postings=median.evidence.count,
        stat_ids=band.stat_ids, evidence=band.evidence,
    )


def _skills(brief: MarketBrief, by_key: dict[str, Posting]) -> RowChart | None:
    stats = {s.id: s for s in brief.stats.stats}
    counts = [
        s for s in brief.stats.stats
        if s.id.startswith("skills.") and s.id.endswith(".count") and _employers(s.evidence.posting_keys, by_key) >= MIN_SKILL_EMPLOYERS
    ]
    counts = sorted(counts, key=lambda s: -s.evidence.count)[:SKILL_ROWS]
    if not counts:
        return None
    rows = []
    for s in counts:
        must = stats.get(s.id.removesuffix(".count") + ".must")
        rows.append(Row(
            label=_name(s), count=s.evidence.count, required=must.evidence.count if must else 0,
            stat_ids=[s.id, *([must.id] if must else [])], evidence=s.evidence,
        ))
    # The label is the only place Analysis records how many Postings had skills extracted.
    extracted = re.search(r"of (\d+) extracted Postings", counts[0].label)
    caption = (f"From {extracted[1]} postings with skills extracted. " if extracted else "") + "Skills only one employer asks for are left out."
    return RowChart(caption=caption, rows=rows)


def _places(sample: list[Posting]) -> RowChart | None:
    deep = [p.region for p in sample if len(p.region) > 1]
    # What every Posting shares (the country, often the state) says nothing, so grouping starts at the next level.
    shared = 0
    while deep and all(len(r) > shared + 1 and r[shared] == deep[0][shared] for r in deep):
        shared += 1
    groups: dict[str, list[str]] = {}
    for p in sample:
        # A country-only region has no area to name, but it doesn't stop the others being grouped.
        groups.setdefault(p.region[shared] if len(p.region) > 1 else NO_AREA, []).append(p.key)
    if len(groups) < 2:
        return None
    ranked = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    rows = [Row(label=name, count=len(keys), stat_ids=[], evidence=Evidence(posting_keys=keys)) for name, keys in ranked[:PLACE_ROWS]]
    if rest := ranked[PLACE_ROWS:]:
        keys = [k for _, ks in rest for k in ks]
        rows.append(Row(label=f"{len(rest)} other places", count=len(keys), stat_ids=[], evidence=Evidence(posting_keys=keys)))
    return RowChart(caption=f"Where {len(sample)} analysed postings are.", rows=rows)


def _employer_chart(brief: MarketBrief) -> RowChart | None:
    top = [s for s in brief.stats.stats if s.id.startswith("competition.employer.")][:EMPLOYER_ROWS]
    if not top:
        return None
    distinct = next((s for s in brief.stats.stats if s.id == "competition.distinct_employers"), None)
    caption = f"{int(distinct.value)} different employers in the analysed postings." if distinct else "Employers in the analysed postings."
    return RowChart(caption=caption, rows=[Row(label=_name(s), count=s.evidence.count, stat_ids=[s.id], evidence=s.evidence) for s in top])


def glance(brief: MarketBrief, postings: list[Posting]) -> Glance:
    by_key = {p.key: p for p in postings}
    return Glance(
        reader_notes=_reader_notes(brief), pay=_pay(brief), skills=_skills(brief, by_key), places=_places(postings),
        employers=_employer_chart(brief),
    )
