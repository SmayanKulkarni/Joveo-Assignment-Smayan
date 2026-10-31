import pytest

from talent_scout.brief.rules import build_insights, fill_gaps, rule_draft
from talent_scout.brief.types import Confidence, InsightDraft
from talent_scout.collection.testing import posting
from talent_scout.kernel.types import Dimension, Evidence, MarketStats, Source, Stat

DIMENSION_OF = {"demand": Dimension.demand, "comp": Dimension.compensation, "skills": Dimension.skills,
                "competition": Dimension.competition, "titles": Dimension.titles_seniority}


def world(*specs, source=Source.usajobs):
    """Stats and Sample from (stat id, postings, employers, value) specs."""
    sample, stats = [], []
    for stat_id, n, employers, *value in specs:
        mine = [posting(f"{stat_id}-{i}", source=source, company=f"{stat_id} employer {i % employers}") for i in range(n)]
        sample += mine
        stats.append(Stat(
            id=stat_id, dimension=DIMENSION_OF[stat_id.split(".")[0]], label=f"label of {stat_id}", value=value[0] if value else n,
            unit=None, evidence=Evidence(posting_keys=[p.key for p in mine]),
        ))
    return MarketStats(sample_size=len(sample), stats=stats), sample


def tag(stats_and_sample, *ids, supported=None):
    stats, sample = stats_and_sample
    verdicts = [] if supported is None else [supported]
    return build_insights(stats, sample, [InsightDraft(text="claim", stat_ids=list(ids))], verdicts)[0]


# The fixture table in the Confidence Tag ticket: Postings/employers from the 125 fixture Postings.
@pytest.mark.parametrize("stat_id, postings, employers, expected", [
    ("competition.direct_share", 68, 42, "high"),
    ("titles.variant.data-engineer", 35, 19, "high"),
    ("comp.disclosed_share", 100, 49, "high"),
    ("comp.federal.median", 25, 12, "medium"),
    ("skills.sql.count", 14, 12, "medium"),
    ("skills.python.count", 18, 17, "medium"),
    ("competition.employer.booz-allen", 23, 1, "medium"),  # exempt from the employer minimum
    ("skills.artificial-intelligence.count", 13, 4, "low"),
    ("skills.pyspark.count", 8, 8, "low"),
    ("comp.estimated.lead.median", 5, 5, "low"),
    ("titles.variant.few-employers", 40, 4, "low"),
    ("competition.employer.small", 9, 1, "low"),  # the exemption doesn't lift the Posting minimum
])
def test_each_stat_rates_by_its_postings_and_employers(stat_id, postings, employers, expected):
    assert tag(world((stat_id, postings, employers)), stat_id).confidence == expected


def test_estimated_pay_is_capped_from_high_to_medium():
    insight = tag(world(("comp.estimated.median", 100, 49)), "comp.estimated.median")
    assert insight.confidence == Confidence.medium and "pay is estimated" in insight.confidence_reason


def test_skills_are_capped_only_when_an_adzuna_posting_is_in_the_sample():
    specs = (("skills.python.count", 40, 20),)
    assert tag(world(*specs, source=Source.adzuna), "skills.python.count").confidence == Confidence.medium
    assert tag(world(*specs, source=Source.usajobs), "skills.python.count").confidence == Confidence.high


@pytest.mark.parametrize("age, expected", [(30.0, Confidence.high), (31.0, Confidence.medium)])
def test_old_data_caps_every_insight(age, expected):
    data = world(("demand.sample_size", 40, 20), ("demand.median_age_days", 40, 20, age))
    assert tag(data, "demand.sample_size").confidence == expected


def test_only_an_unsupported_verdict_caps_and_a_missing_one_does_not():
    data = world(("demand.sample_size", 40, 20))
    assert tag(data, "demand.sample_size").confidence == Confidence.high
    assert tag(data, "demand.sample_size", supported=True).confidence == Confidence.high
    capped = tag(data, "demand.sample_size", supported=False)
    assert capped.confidence == Confidence.medium and "critic couldn't confirm it" in capped.confidence_reason


def test_an_insight_takes_its_weakest_stat_and_the_reason_names_it_and_the_cap():
    data = world(("demand.sample_size", 125, 49), ("skills.python.count", 18, 17), source=Source.adzuna)
    insight = tag(data, "demand.sample_size", "skills.python.count")
    assert insight.confidence_reason == "Medium: weakest cited Stat has 18 Postings from 17 employers; skills come from snippets"
    weak = tag(world(("demand.sample_size", 125, 49), ("skills.pyspark.count", 8, 8)), "demand.sample_size", "skills.pyspark.count")
    assert weak.confidence == Confidence.low and weak.confidence_reason == "Low: weakest cited Stat has 8 Postings from 8 employers"


def test_evidence_is_the_union_of_cited_postings_and_dimension_is_the_first_cited():
    stats, sample = world(("skills.a.count", 6, 6), ("demand.sample_size", 12, 12))
    insight = tag((stats, sample), "skills.a.count", "demand.sample_size")
    assert insight.dimension == Dimension.skills and insight.evidence.count == 18


def test_a_posting_with_no_company_is_its_own_employer():
    stats, sample = world(("skills.a.count", 10, 1))
    nameless = [p.model_copy(update={"company": None}) for p in sample]
    assert tag((stats, sample), "skills.a.count").confidence == Confidence.low
    assert tag((stats, nameless), "skills.a.count").confidence_reason.endswith("10 Postings from 10 employers")


def three_dimensions():
    return [("demand.sample_size", 12, 12), ("skills.a.count", 12, 12), ("titles.variant.x", 12, 12)]


def test_fill_gaps_adds_the_first_stat_of_each_uncovered_dimension_after_the_writers_insights():
    stats, _ = world(*three_dimensions())
    insights = build_insights(stats, world(*three_dimensions())[1], [InsightDraft(text="mine", stat_ids=["skills.a.count"])], [])
    assert [(i.text, i.stat_ids) for i in insights] == [
        ("mine", ["skills.a.count"]), ("label of demand.sample_size", ["demand.sample_size"]), ("label of titles.variant.x", ["titles.variant.x"]),
    ]


def test_fill_gaps_skips_a_thin_sample_unless_no_insight_survived():
    stats = MarketStats(sample_size=9, stats=world(*[(i, 3, 3) for i, *_ in three_dimensions()])[0].stats)
    some = [InsightDraft(text="mine", stat_ids=["skills.a.count"])]
    assert fill_gaps(stats, some) == []
    assert [d.stat_ids for d in fill_gaps(stats, [])] == [["demand.sample_size"], ["skills.a.count"], ["titles.variant.x"]]


def test_rule_draft_cites_the_sample_size_and_covers_every_dimension():
    stats, _ = world(*three_dimensions())
    draft = rule_draft(stats)
    assert draft.summary_stat_ids == ["demand.sample_size"] and f"{stats.sample_size} Postings" in draft.summary
    assert [i.stat_ids for i in draft.insights] == [["demand.sample_size"], ["skills.a.count"], ["titles.variant.x"]]


def test_rule_draft_keeps_a_thin_sample_to_the_thin_cap():
    stats = MarketStats(sample_size=5, stats=world(*[(i, 5, 5) for i in ("demand.a", "comp.a", "skills.a", "titles.a")])[0].stats)
    assert len(rule_draft(stats).insights) == 3
