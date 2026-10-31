import re
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import date
from statistics import median, quantiles

from talent_scout.analysis.types import EmployerType, Extraction, Requirement
from talent_scout.kernel.state import State
from talent_scout.kernel.text import employer_key, fold
from talent_scout.kernel.types import (
    ADZUNA_CURRENCY, Dimension, Evidence, HiringRequest, MarketStats, PayPeriod, Posting, SearchPlan, Source, Stat,
)

TOP_SKILLS, TOP_EMPLOYERS, TOP_TITLES = 15, 10, 10
MIN_YEARS_FIGURES = 5
MIN_PAY_FIGURES = 5
MIN_ANNUAL_USD = 1000
TREND_DAYS = 14
MIN_TREND_POSTINGS = 20
TREND_NOTE = "Ads still live, which tilts recent because filled ads disappear."

KNOWN_AGENCIES = frozenset({
    "randstad", "adecco", "manpowergroup", "robert half", "kforce", "insight global", "teksystems", "hays",
    "michael page", "kelly services", "aerotek", "allegis",
})

# Units of each currency per USD, from ECB reference rates. Refresh both by hand.
FX_DATE = "2026-10-30"
UNITS_PER_USD = {
    "AUD": 1.4236, "BRL": 5.4325, "CAD": 1.3969, "CHF": 0.8230, "EUR": 0.8951, "GBP": 0.7463, "INR": 94.9552,
    "MXN": 18.9077, "NZD": 1.7743, "PLN": 3.9418, "SGD": 1.2784, "USD": 1.0, "ZAR": 16.6895,
}
ANNUAL = {
    PayPeriod.annual: 1, PayPeriod.unknown: 1, PayPeriod.hourly: 2080, PayPeriod.daily: 260,
    PayPeriod.weekly: 52, PayPeriod.biweekly: 26, PayPeriod.monthly: 12,
}
# Groups are never pooled; only the first two get seniority slices.
PAY_GROUPS = {"advertised": "Advertised", "estimated": "Adzuna-estimated", "federal": "Federal"}
SLICED_GROUPS = ("advertised", "estimated")

_REQUIREMENT_RANK ={Requirement.unstated: 0, Requirement.nice: 1, Requirement.must: 2}
_EMPLOYER_TYPE_NAME = {
    EmployerType.direct: "direct employers",
    EmployerType.agency: "staffing agencies",
    EmployerType.unknown: "employers of unknown type, or with no company",
}


def mentions(term: str, text: str) -> bool:
    # An empty term would match between any two words.
    return bool(term) and re.search(rf"(?<![\w+#]){re.escape(term)}(?![\w+#])", text) is not None


def _stat(id: str, dimension: Dimension, label: str, value: float | str, unit: str | None, keys: list[str]) -> Stat:
    return Stat(id=id, dimension=dimension, label=label, value=value, unit=unit, evidence=Evidence(posting_keys=keys))


def _slug(folded: str) -> str:
    return folded.replace(" ", "-")


def _share(n: int, total: int) -> float:
    return round(n / total, 3)


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _common(spellings: Counter) -> str:
    return min(spellings, key=lambda s: (-spellings[s], s))


def _group(sample: list[Posting], key_of: Callable[[Posting], str | None], spelling_of: Callable[[Posting], str]) -> list[tuple[str, str, list[str]]]:
    """(key, most common spelling, Posting keys) per group, biggest first, ties by key."""
    members: dict[str, list[str]] = defaultdict(list)
    spellings: dict[str, Counter] = defaultdict(Counter)
    for p in sample:
        if key := key_of(p):
            members[key].append(p.key)
            spellings[key][spelling_of(p)] += 1
    groups = [(k, _common(spellings[k]), keys) for k, keys in members.items()]
    return sorted(groups, key=lambda g: (-len(g[2]), g[0]))


# demand


def _trend(ages: dict[str, int]) -> tuple[str, list[str], int, int] | None:
    newer = [k for k, a in ages.items() if a < TREND_DAYS]
    older = [k for k, a in ages.items() if TREND_DAYS <= a < 2 * TREND_DAYS]
    if len(newer) + len(older) < MIN_TREND_POSTINGS:
        return None
    # Integer ratios, so exactly 1.25x and 0.8x land on the stated side. An empty older window is always rising.
    if len(newer) * 4 >= len(older) * 5:
        direction = "rising"
    elif len(newer) * 5 <= len(older) * 4:
        direction = "falling"
    else:
        direction = "flat"
    return direction, newer + older, len(newer), len(older)


def _demand(sample: list[Posting], now: date | None, max_days_old: int | None) -> list[Stat]:
    d = Dimension.demand
    stats = [_stat("demand.sample_size", d, "Postings in the Sample", len(sample), "postings", [p.key for p in sample])]
    if now is None:
        return stats
    ages = {p.key: (now - p.posted_at).days for p in sample}
    for days in (7, 30):
        keys = [k for k, a in ages.items() if a < days]
        if keys:
            stats.append(_stat(f"demand.posted_{days}d", d, f"Postings from the last {days} days", len(keys), "postings", keys))
    stats.append(_stat("demand.median_age_days", d, "Median age of Postings in the Sample", float(median(ages.values())), "days", list(ages)))
    if max_days_old is not None and max_days_old >= 2 * TREND_DAYS and (trend := _trend(ages)):
        direction, keys, newer, older = trend
        label = f"Posting trend, newest {TREND_DAYS} days ({newer} Postings) against the {TREND_DAYS} before ({older}). {TREND_NOTE}"
        stats.append(_stat("demand.trend", d, label, direction, None, keys))
    return stats


# compensation


def _pay_group(p: Posting) -> str:
    if p.source == Source.usajobs:
        return "federal"
    return "estimated" if p.salary.predicted else "advertised"


def _pay_stats(prefix: str, name: str, scope: str, figures: dict[str, float], origin: dict[str, str], currency: str) -> list[Stat]:
    unit = f"{currency}/year"
    converted = sorted({origin[k] for k in figures} - {currency})
    note = f", converted from {', '.join(converted)}" if converted else ""
    # Inclusive, since exclusive can land outside the data on small groups.
    p25, mid, p75 = quantiles(figures.values(), n=4, method="inclusive")
    return [
        _stat(f"{prefix}.{suffix}", Dimension.compensation, f"{name} {wording} pay{scope}, {_plural(len(figures), 'Posting')}, {unit}{note}", float(round(v)), unit, list(figures))
        for suffix, wording, v in (("median", "median", mid), ("p25", "25th percentile", p25), ("p75", "75th percentile", p75))
    ]


def _pay(sample: list[Posting], extracted: dict[str, Extraction], request: HiringRequest | None, plan: SearchPlan | None) -> tuple[list[Stat], list[str]]:
    if plan is None:
        return [], []
    caveats = []
    asked = request.currency if request else None
    if asked in UNITS_PER_USD:
        currency = asked
    else:
        currency = ADZUNA_CURRENCY[plan.country]
        if asked:
            caveats.append(f"Currency unavailable: {asked} has no exchange rate, so pay is shown in {currency}")
    per_usd = UNITS_PER_USD[currency]

    # Per group: Posting key -> annual figure in the Stat currency, plus each figure's own currency and period.
    figures: dict[str, dict[str, float]] = {g: {} for g in PAY_GROUPS}
    origin: dict[str, str] = {}
    unknown_period: dict[str, set[str]] = {g: set() for g in PAY_GROUPS}
    for p in (p for p in sample if p.salary):
        s = p.salary
        bounds = [b for b in (s.min, s.max) if b is not None]
        group = _pay_group(p)
        figures[group][p.key] = sum(bounds) / len(bounds) * ANNUAL[s.period] / UNITS_PER_USD[s.currency] * per_usd
        origin[p.key] = s.currency
        if s.period == PayPeriod.unknown:
            unknown_period[group].add(p.key)

    stats, reached, excluded = [], set(), 0
    for group, name in PAY_GROUPS.items():
        group_figures = figures[group]
        if not group_figures:
            continue
        # Only a figure with no period can be hourly or monthly, so only those are held to the plausibility rules.
        cutoff = max(MIN_ANNUAL_USD * per_usd, median(group_figures.values()) / 6)
        implausible = {k for k in unknown_period[group] if group_figures[k] < cutoff}
        excluded += len(implausible)
        kept = {k: v for k, v in group_figures.items() if k not in implausible}
        if len(kept) < MIN_PAY_FIGURES:
            continue
        reached.add(group)
        stats += _pay_stats(f"comp.{group}", name, "", kept, origin, currency)
        if group not in SLICED_GROUPS:
            continue
        by_level: dict[str, dict[str, float]] = defaultdict(dict)
        for k, v in kept.items():
            if k in extracted:
                by_level[extracted[k].seniority][k] = v
        for level, level_figures in sorted(by_level.items()):
            if len(level_figures) >= MIN_PAY_FIGURES:
                stats += _pay_stats(f"comp.{group}.{level}", name, f" at {level} level", level_figures, origin, currency)

    # An estimate isn't disclosure and USAJOBS must publish pay, so only Adzuna Postings are counted.
    adzuna = [p.key for p in sample if p.source == Source.adzuna]
    for group, id, wording in (("advertised", "disclosed", "advertised"), ("estimated", "estimated", "Adzuna-estimated")):
        if adzuna:
            n = len(figures[group])
            share = _share(n, len(adzuna))
            label = f"Adzuna Postings with {wording} pay: {share:.1%} ({n} of {len(adzuna)})"
            stats.append(_stat(f"comp.{id}_share", Dimension.compensation, label, share, "share", adzuna))

    if "estimated" in reached and "advertised" not in reached:
        caveats.append(f"Pay is estimated: fewer than {MIN_PAY_FIGURES} advertised salaries, so pay comes from Adzuna's own estimates")
    if not reached:
        caveats.append(f"Too little pay data: no pay group has {MIN_PAY_FIGURES} salaries")
    if assumed := len(unknown_period["advertised"]):
        caveats.append(f"Pay period assumed: treated as annual for {_plural(assumed, 'advertised figure')} with no pay period")
    if excluded:
        caveats.append(f"Implausible pay excluded: {_plural(excluded, 'figure')} with no pay period, too low to be annual pay")
    if converted := sum(c != currency for c in origin.values()):
        caveats.append(f"Pay converted: {_plural(converted, 'Posting')} paid in another currency, converted to {currency} at ECB rates of {FX_DATE}")
    return stats, caveats


# skills


def _skills(sample: list[Posting], extracted: dict[str, Extraction], aliases: dict[str, str]) -> list[Stat]:
    # Per skill: Posting key -> strongest requirement, with the spellings seen and any canonical name from an alias.
    found: dict[str, dict[str, Requirement]] = defaultdict(dict)
    spellings: dict[str, Counter] = defaultdict(Counter)
    canonical_names: dict[str, str] = {}
    employer_of = {p.key: employer_key(p.company) or p.key for p in sample}  # no company: its own employer
    for p in sample:
        if p.key not in extracted:
            continue
        for mention in extracted[p.key].skills:
            folded = fold(mention.name)
            if not folded:
                continue
            canonical = aliases.get(folded)
            key = (fold(canonical) if canonical else "") or folded
            if canonical:
                canonical_names.setdefault(key, canonical)
            else:
                spellings[key][mention.name] += 1
            seen = found[key].get(p.key, Requirement.unstated)
            found[key][p.key] = max(seen, mention.requirement, key=_REQUIREMENT_RANK.get)

    def rank(item):
        key, postings = item
        return -len({employer_of[k] for k in postings}), -len(postings), key

    total, s = len(extracted), Dimension.skills
    stats = []
    for key, postings in sorted(found.items(), key=rank)[:TOP_SKILLS]:
        name = canonical_names.get(key) or _common(spellings[key])
        employers = len({employer_of[k] for k in postings})
        label = f"{name}: {len(postings)} of {total} extracted Postings, from {_plural(employers, 'employer')}"
        stats.append(_stat(f"skills.{_slug(key)}.count", s, label, len(postings), "postings", list(postings)))
        for level, wording in ((Requirement.must, "required"), (Requirement.nice, "nice to have")):
            keys = [k for k, r in postings.items() if r == level]
            if keys:
                stats.append(_stat(f"skills.{_slug(key)}.{level}", s, f"{name}: {wording} in {len(keys)} of {total} extracted Postings", len(keys), "postings", keys))

    years = {k: e.years_min for k, e in extracted.items() if e.years_min is not None}
    if len(years) >= MIN_YEARS_FIGURES:
        label = f"Median minimum years of experience, from {len(years)} of {total} extracted Postings that state one"
        stats.append(_stat("skills.years_median", s, label, float(median(years.values())), "years", list(years)))
    return stats


# competition


def _employer_type(name: str, postings: list[Posting], extracted: dict[str, Extraction]) -> EmployerType:
    if any(p.source == Source.usajobs for p in postings):
        return EmployerType.direct
    words = name.split()
    if any(w == "staffing" or w.startswith("recruit") for w in words) or any(mentions(a, name) for a in KNOWN_AGENCIES):
        return EmployerType.agency
    votes = Counter(extracted[p.key].employer_type for p in postings if p.key in extracted)
    direct, agency = votes[EmployerType.direct], votes[EmployerType.agency]
    return EmployerType.direct if direct > agency else EmployerType.agency if agency > direct else EmployerType.unknown


def _competition(sample: list[Posting], extracted: dict[str, Extraction]) -> list[Stat]:
    c, total = Dimension.competition, len(sample)
    by_key = {p.key: p for p in sample}
    employers = _group(sample, lambda p: employer_key(p.company), lambda p: p.company)
    stats = [
        _stat(f"competition.employer.{_slug(key)}", c, f"{name}: {len(keys)} of {total} Postings in the Sample", len(keys), "postings", keys)
        for key, name, keys in employers[:TOP_EMPLOYERS]
    ]
    named = [k for _, _, keys in employers for k in keys]
    if named:
        stats.append(_stat("competition.distinct_employers", c, "Distinct employers in the Sample", len(employers), "employers", named))

    # A Posting with no company has no employer to type, so it only ever counts as unknown.
    by_type: dict[EmployerType, list[str]] = {t: [] for t in EmployerType}
    with_company = set(named)
    by_type[EmployerType.unknown] += [p.key for p in sample if p.key not in with_company]
    for key, _, keys in employers:
        by_type[_employer_type(key, [by_key[k] for k in keys], extracted)] += keys
    for kind, keys in by_type.items():
        if keys:
            share = _share(len(keys), total)
            label = f"Postings from {_EMPLOYER_TYPE_NAME[kind]}: {share:.1%} ({len(keys)} of {total} in the Sample)"
            stats.append(_stat(f"competition.{kind}_share", c, label, share, "share", keys))
    return stats


# titles and seniority


def _titles(sample: list[Posting], extracted: dict[str, Extraction]) -> list[Stat]:
    t, total = Dimension.titles_seniority, len(sample)
    titles = _group(sample, lambda p: fold(p.title), lambda p: p.title)
    stats = [
        _stat(f"titles.variant.{_slug(key)}", t, f"{name}: {len(keys)} of {total} Postings in the Sample", len(keys), "postings", keys)
        for key, name, keys in titles[:TOP_TITLES]
    ]
    if titles:
        stats.append(_stat("titles.distinct", t, "Distinct titles in the Sample", len(titles), "titles", [k for _, _, keys in titles for k in keys]))

    levels: dict[str, list[str]] = defaultdict(list)
    for key, e in extracted.items():
        levels[e.seniority].append(key)
    for level, keys in sorted(levels.items()):
        share = _share(len(keys), len(extracted))
        label = f"Share of extracted Postings at {level} level: {share:.1%} ({len(keys)} of {len(extracted)})"
        stats.append(_stat(f"seniority.{level}", t, label, share, "share", keys))
    return stats


# entry point


def _now(state: State) -> date | None:
    # The newest fetch, never the clock: a clock would change Stats and miss every downstream LLM cache entry on replay.
    fetched = [o.fetched_at for r in state.fetches if r.result for o in r.result.sources.values()]
    return max(fetched).date() if fetched else None


def compute_stats(state: State) -> tuple[MarketStats, list[str], dict]:
    """The Stats, the Caveat messages and the data for the run-log note. Pure: the same state gives the same result."""
    sample = sorted(state.sample_postings, key=lambda p: p.key)
    extracted = {p.key: state.extractions[p.key] for p in sample if p.key in state.extractions}
    if not sample:
        return MarketStats(sample_size=0, stats=[]), [], {"sample_size": 0, "extracted": 0, "stats": 0, "ungrounded": 0}

    plan = state.current_plan
    pay_stats, pay_caveats = _pay(sample, extracted, state.hiring_request, plan)
    stats = [
        *_demand(sample, _now(state), plan.max_days_old if plan else None),
        *pay_stats,
        *_skills(sample, extracted, state.skill_aliases),
        *_competition(sample, extracted),
        *_titles(sample, extracted),
    ]

    caveats = []
    if missing := len(sample) - len(extracted):
        caveats.append(f"Postings not extracted: {missing} of {len(sample)} Postings have no Extraction")
    if snippets := sum(p.source == Source.adzuna for p in sample):
        caveats.append(f"Skills from snippets: {snippets} Adzuna Postings give 500-character snippets, which undercount skills")
    caveats += pay_caveats
    summary = {
        "sample_size": len(sample), "extracted": len(extracted), "stats": len(stats),
        "ungrounded": sum(e.ungrounded for e in extracted.values()),
    }
    return MarketStats(sample_size=len(sample), stats=stats), caveats, summary
