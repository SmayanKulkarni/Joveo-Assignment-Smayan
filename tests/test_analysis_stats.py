import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from talent_scout.analysis.nodes import make_nodes
from talent_scout.analysis.stats import compute_stats
from talent_scout.analysis.types import EmployerType, Extraction, Requirement, Seniority, SkillMention
from talent_scout.collection.testing import FETCHED_AT, make_deps, plan, posting, record, state_with
from talent_scout.kernel.state import LogKind
from talent_scout.kernel.types import MarketStats, Source

NOW = FETCHED_AT.date()


def ex(*skills, seniority=Seniority.mid, employer=EmployerType.direct, years=None, ungrounded=0) -> Extraction:
    """Skills are names, or (name, Requirement) pairs."""
    mentions = [SkillMention(name=s, requirement=Requirement.unstated) if isinstance(s, str) else SkillMention(name=s[0], requirement=s[1]) for s in skills]
    return Extraction(skills=mentions, seniority=seniority, years_min=years, employer_type=employer, ungrounded=ungrounded)


def nameless(id: str, **kw):
    return posting(id, **kw).model_copy(update={"company": None})


def state(postings, extractions=None, **over):
    base = dict(
        postings={p.key: p for p in postings}, sample=[p.key for p in postings],
        extractions={p.key: e for p, e in zip(postings, extractions or [], strict=False)},
        fetches=[record([], fetched_at=FETCHED_AT)],
    )
    return state_with(**{**base, **over})


def stats_of(s) -> dict:
    return {st.id: st for st in compute_stats(s)[0].stats}


def values(s, prefix: str) -> dict:
    return {i: st.value for i, st in stats_of(s).items() if i.startswith(prefix)}


# General


def test_a_sample_of_zero_gives_empty_stats_and_no_caveats():
    stats, caveats, summary = compute_stats(state_with())
    assert stats == MarketStats(sample_size=0, stats=[]) and caveats == []
    assert summary == {"sample_size": 0, "extracted": 0, "stats": 0, "ungrounded": 0}


def test_now_is_the_newest_fetched_at_not_the_clock_and_runs_are_identical():
    ages = (2, 12, 40)
    postings = [posting(str(a), posted=NOW - timedelta(days=a)) for a in ages]
    older_fetch = record([], fetched_at=FETCHED_AT - timedelta(days=9))
    s = state(postings, fetches=[older_fetch, record([], fetched_at=FETCHED_AT)])

    got = stats_of(s)
    assert got["demand.posted_7d"].value == 1 and got["demand.posted_30d"].value == 2
    assert got["demand.median_age_days"].value == 12

    # Same Stats whatever order the Sample and Extractions arrive in.
    flipped = s.model_copy(update={"sample": s.sample[::-1]})
    assert compute_stats(s) == compute_stats(s) == compute_stats(flipped)


def test_without_any_fetch_the_age_stats_are_omitted_rather_than_read_from_the_clock():
    s = state([posting("a")]).model_copy(update={"fetches": []})
    got = stats_of(s)
    assert "demand.sample_size" in got
    assert not {"demand.posted_7d", "demand.posted_30d", "demand.median_age_days", "demand.trend"} & set(got)


def test_every_evidence_key_is_within_the_sample():
    inside = [posting(str(i), company=f"Co {i % 3}", title=f"T{i % 2}", posted=NOW - timedelta(days=i)) for i in range(30)]
    inside.append(nameless("nameless"))
    outside = posting("outside")
    extractions = [ex("Python", ("SQL", Requirement.must), years=3, seniority=Seniority.senior) for _ in inside]
    s = state(inside, extractions)
    # A Posting outside the Sample must never reach a Stat, even with an Extraction.
    s = s.model_copy(update={"postings": {**s.postings, outside.key: outside}, "extractions": {**s.extractions, outside.key: ex("Rust")}})
    got = compute_stats(s)[0].stats
    # Every family is present, so the check below covers each of them.
    ids = {st.id for st in got}
    assert {"demand.trend", "skills.python.count", "skills.sql.must", "skills.years_median", "competition.direct_share", "titles.distinct", "seniority.senior"} <= ids
    assert all(set(st.evidence.posting_keys) <= set(s.sample) and st.evidence.count for st in got)
    assert "skills.rust.count" not in {st.id for st in got}


def test_labels_name_the_extracted_denominator_and_shares_carry_a_rounded_percentage():
    s = state([posting("a"), posting("b"), posting("c")], [ex("Python", seniority=Seniority.senior), ex(), ex()])
    got = stats_of(s)
    assert got["skills.python.count"].label == "Python: 1 of 3 extracted Postings, from 1 employer"
    assert got["seniority.senior"].value == 0.333
    assert got["seniority.senior"].label == "Share of extracted Postings at senior level: 33.3% (1 of 3)"


def test_lists_are_capped_and_empty_windows_and_levels_are_omitted():
    n = 20
    s = state(
        [posting(str(i), company=f"Co {i}", title=f"Title {i}", posted=NOW - timedelta(days=100)) for i in range(n)],
        [ex(f"Skill {i}") for i in range(n)],
    )
    got = stats_of(s)
    assert len(values(s, "skills.")) == 15 and len(values(s, "competition.employer.")) == 10 and len(values(s, "titles.variant.")) == 10
    # Nothing was posted in the last 7 or 30 days, and no Posting says must or nice.
    assert not {"demand.posted_7d", "demand.posted_30d"} & set(got)
    assert not [i for i in got if i.endswith((".must", ".nice"))]


# Skills


def test_an_alias_and_its_canonical_name_in_one_posting_count_once_and_must_wins():
    both = ex(("Postgres", Requirement.nice), ("PostgreSQL", Requirement.must))
    s = state([posting("a"), posting("b")], [both, ex("Postgres")], skill_aliases={"postgres": "PostgreSQL"})
    got = stats_of(s)
    assert got["skills.postgresql.count"].value == 2
    assert got["skills.postgresql.count"].label.startswith("PostgreSQL: 2 of 2")
    assert got["skills.postgresql.must"].value == 1
    assert "skills.postgresql.nice" not in got and "skills.postgres.count" not in got


def test_a_skill_without_an_alias_shows_its_most_common_spelling():
    s = state([posting("a"), posting("b"), posting("c")], [ex("pandas"), ex("Pandas"), ex("Pandas")])
    assert stats_of(s)["skills.pandas.count"].label.startswith("Pandas: 3 of 3")


def test_skills_rank_by_employers_before_postings_and_a_posting_without_company_is_its_own_employer():
    one_company = [posting(str(i), company="Booz Allen") for i in range(3)]
    two_companies = [posting("x", company="Acme"), posting("y", company="Beta")]
    s = state([*one_company, *two_companies], [ex("Boilerplate")] * 3 + [ex("Real")] * 2)
    counts = [i for i in values(s, "skills.") if i.endswith(".count")]
    assert counts == ["skills.real.count", "skills.boilerplate.count"]
    assert stats_of(s)["skills.real.count"].label == "Real: 2 of 5 extracted Postings, from 2 employers"

    solo = state([nameless("p"), nameless("q")], [ex("Go")] * 2)
    assert stats_of(solo)["skills.go.count"].label == "Go: 2 of 2 extracted Postings, from 2 employers"


def test_years_median_needs_five_figures():
    four = state([posting(str(i)) for i in range(4)], [ex(years=i + 1) for i in range(4)])
    assert "skills.years_median" not in stats_of(four)
    five = state([posting(str(i)) for i in range(5)], [ex(years=i + 1) for i in range(5)])
    assert stats_of(five)["skills.years_median"].value == 3


# Employers and titles


def test_employers_group_without_legal_suffixes_and_no_company_counts_only_towards_unknown():
    named = [posting("1", company="Acme Inc"), posting("2", company="Acme Inc"), posting("3", company="ACME, LLC")]
    s = state([*named, nameless("4")], [ex(employer=EmployerType.direct)] * 3 + [ex(employer=EmployerType.direct)])
    got = stats_of(s)
    assert got["competition.employer.acme"].value == 3
    assert got["competition.employer.acme"].label == "Acme Inc: 3 of 4 Postings in the Sample"
    assert got["competition.distinct_employers"].value == 1
    assert got["competition.unknown_share"].value == 0.25
    assert got["competition.unknown_share"].evidence.posting_keys == ["adzuna:4"]
    assert got["competition.direct_share"].value == 0.75


def employer_shares(company, types, source=Source.adzuna):
    postings = [posting(str(i), company=company, source=source) for i in range(len(types))]
    return values(state(postings, [ex(employer=t) for t in types]), "competition.")


def test_a_booz_style_split_resolves_by_majority_and_a_tie_is_unknown():
    d, a = EmployerType.direct, EmployerType.agency
    split = employer_shares("Booz Allen Hamilton", [d] * 2 + [a] * 3)
    assert split["competition.agency_share"] == 1.0 and "competition.direct_share" not in split
    tie = employer_shares("Booz Allen Hamilton", [d, a])
    assert tie["competition.unknown_share"] == 1.0
    nothing_known = employer_shares("Booz Allen Hamilton", [EmployerType.unknown] * 2)
    assert nothing_known["competition.unknown_share"] == 1.0


def test_randstad_is_an_agency_with_any_model_answer_and_usajobs_is_direct():
    for t in EmployerType:
        assert employer_shares("Randstad Technologies", [t])["competition.agency_share"] == 1.0
    assert employer_shares("Acme Staffing", [EmployerType.direct])["competition.agency_share"] == 1.0
    assert employer_shares("Talent Recruitment Ltd", [EmployerType.direct])["competition.agency_share"] == 1.0
    federal = employer_shares("Department of Energy", [EmployerType.agency], source=Source.usajobs)
    assert federal["competition.direct_share"] == 1.0


def test_titles_group_by_folded_title_only_and_are_ranked_by_count():
    titles = ["Data Engineer", "data  engineer", "Data Engineer", "Data Engineer - Java"]
    s = state([posting(str(i), title=t) for i, t in enumerate(titles)])
    got = stats_of(s)
    assert got["titles.variant.data-engineer"].value == 3
    assert got["titles.variant.data-engineer"].label == "Data Engineer: 3 of 4 Postings in the Sample"
    assert got["titles.variant.data-engineer-java"].value == 1
    assert got["titles.distinct"].value == 2
    assert list(values(s, "titles.variant.")) == ["titles.variant.data-engineer", "titles.variant.data-engineer-java"]


# Trend


def trend_state(newer, older, *, max_days_old=30, outside=0):
    ages = [0] * newer + [20] * older + [40] * outside
    return state([posting(str(i), posted=NOW - timedelta(days=a)) for i, a in enumerate(ages)], search_plan=plan(max_days_old=max_days_old))


@pytest.mark.parametrize(
    ("newer", "older", "expected"),
    [(25, 20, "rising"), (24, 20, "flat"), (16, 20, "falling"), (17, 20, "flat"), (20, 0, "rising"), (0, 20, "falling")],
)
def test_trend_thresholds(newer, older, expected):
    assert stats_of(trend_state(newer, older))["demand.trend"].value == expected


@pytest.mark.parametrize(
    ("newer", "older", "max_days_old", "outside"),
    [(25, 20, 27, 0), (10, 9, 30, 0), (10, 9, 30, 5), (19, 0, 30, 0)],
)
def test_trend_minimums(newer, older, max_days_old, outside):
    assert "demand.trend" not in stats_of(trend_state(newer, older, max_days_old=max_days_old, outside=outside))


def test_trend_is_present_at_exactly_the_minimums_and_its_label_says_ads_are_live():
    trend = stats_of(trend_state(10, 10, max_days_old=28))["demand.trend"]
    assert trend.value == "flat" and trend.evidence.count == 20
    assert "Ads still live, which tilts recent because filled ads disappear." in trend.label


# Caveats and the Run log


def test_postings_not_extracted_caveat_fires_with_the_count_and_not_when_all_are_extracted():
    postings = [posting("a"), posting("b"), posting("c")]
    _, caveats, _ = compute_stats(state(postings, [ex(), ex()]))
    assert [c for c in caveats if c.startswith("Postings not extracted")] == ["Postings not extracted: 1 of 3 Postings have no Extraction"]
    _, caveats, _ = compute_stats(state(postings, [ex(), ex(), ex()]))
    assert not [c for c in caveats if c.startswith("Postings not extracted")]


def test_skills_from_snippets_caveat_counts_adzuna_postings_and_not_usajobs():
    postings = [posting("a"), posting("b"), posting("c", source=Source.usajobs)]
    _, caveats, _ = compute_stats(state(postings, [ex()] * 3))
    assert [c for c in caveats if c.startswith("Skills from snippets")] == [
        "Skills from snippets: 2 Adzuna Postings give 500-character snippets, which undercount skills"
    ]
    _, caveats, _ = compute_stats(state([posting("c", source=Source.usajobs)], [ex()]))
    assert not [c for c in caveats if c.startswith("Skills from snippets")]


def test_the_node_writes_stats_caveats_and_one_note_with_the_summary():
    postings = [posting("a"), posting("b")]
    s = state(postings, [ex("Python", ungrounded=2)])
    deps, *_ = make_deps()

    update = asyncio.run(make_nodes(deps)["stats"](s))

    assert update["stats"] == compute_stats(s)[0]
    log = update["run_log"]
    assert [e.kind for e in log] == [LogKind.caveat, LogKind.caveat, LogKind.note]
    note = log[-1]
    assert note.node == "stats" and note.data == {"sample_size": 2, "extracted": 1, "stats": len(update["stats"].stats), "ungrounded": 2}
