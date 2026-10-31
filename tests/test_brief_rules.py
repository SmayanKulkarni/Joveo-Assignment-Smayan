import pytest

from talent_scout.brief.rules import build_insights, fill_gaps, outlook, recommendations, request_level, rule_draft
from talent_scout.brief.types import Confidence, InsightDraft
from talent_scout.collection.testing import posting
from talent_scout.kernel.types import Dimension, Evidence, HiringRequest, MarketStats, Source, Stat

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
            unit="USD/year" if stat_id.startswith("comp.") else None, evidence=Evidence(posting_keys=[p.key for p in mine]),
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


def request(seniority=None):
    return HiringRequest(
        role="Data Analyst", location="Austin", country="us", seniority=seniority, employment_type=None,
        work_mode=None, currency=None, purpose=None,
    )


def rate(values, n=125, seniority=None):
    """The outlook for a Sample of n Postings holding one Stat per id, each with its own id as Evidence."""
    stats = [
        Stat(id=i, dimension=Dimension.demand, label=i, value=v, unit=None, evidence=Evidence(posting_keys=[i]))
        for i, v in values.items()
    ]
    return outlook(MarketStats(sample_size=n, stats=stats), request(seniority))


@pytest.mark.parametrize("seniority, level", [
    ("Junior", "entry"), ("entry-level", "entry"), ("graduate", "entry"), ("mid", "mid"), ("Sr. Engineer", "senior"),
    ("principal", "lead"), ("staff", "lead"), ("VP", "executive"), ("head of data", "executive"),
    ("5+ years", None), ("seasoned", None), (None, None),
])
def test_the_requests_level_comes_from_the_word_table(seniority, level):
    assert request_level(request(seniority)) == level


def test_under_the_minimum_the_outlook_is_a_stated_default_with_no_stats():
    result = rate({"competition.distinct_employers": 25}, n=19, seniority="senior")
    assert result.rating == "competitive" and result.stat_ids == [] and result.evidence.count == 0
    assert "Only 19 Postings" in result.reason and "default rather than a finding" in result.reason
    assert "demand, not candidates" in result.reason


def test_many_employers_and_a_high_bar_is_hard_to_fill_and_cites_what_decided_it():
    values = {"competition.distinct_employers": 61, "skills.years_median": 6.0, "demand.trend": "rising"}
    result = rate(values)
    assert result.rating == "hard_to_fill" and result.stat_ids == list(values)
    assert result.evidence.posting_keys == sorted(values)
    assert "61 employers across 125 Postings, with a median of 6 years asked, a rising trend. Postings show demand, not candidates" in result.reason
    assert rate(values) == result  # identical Stats, identical result


@pytest.mark.parametrize("values, expected", [
    ({"competition.distinct_employers": 61, "skills.years_median": 4.0, "demand.trend": "rising"}, "competitive"),  # the fixture
    ({"competition.distinct_employers": 61, "skills.years_median": 5.0}, "hard_to_fill"),
    ({"competition.distinct_employers": 19, "skills.years_median": 5.0}, "competitive"),
    ({"competition.distinct_employers": 61, "skills.years_median": 5.0, "demand.trend": "falling"}, "competitive"),  # falling blocks
    ({"competition.distinct_employers": 5, "skills.years_median": 2.0}, "favourable"),
    ({"competition.distinct_employers": 5, "skills.years_median": 2.0, "demand.trend": "rising"}, "competitive"),  # rising blocks
    ({"competition.distinct_employers": 10, "skills.years_median": 2.0}, "competitive"),
    ({"competition.distinct_employers": 25, "skills.years_median": 2.0, "demand.trend": "rising"}, "competitive"),  # a trend alone rates nothing
    ({"competition.distinct_employers": 5, "skills.years_median": 6.0}, "competitive"),  # few employers but a high bar
    ({"skills.years_median": 6.0}, "competitive"),  # no employer stat
])
def test_each_row_of_the_table_first_match_winning(values, expected):
    assert rate(values).rating == expected


def test_an_unknown_bar_cannot_reach_favourable_but_a_known_one_can():
    few = {"competition.distinct_employers": 5}
    assert rate(few).rating == "competitive"
    assert rate(few, seniority="mid").rating == "favourable"
    assert rate({**few, "seniority.entry": 0.8}).rating == "favourable"  # any seniority stat makes the bar known


def test_a_stated_senior_level_makes_a_high_bar_and_other_words_do_not():
    many = {"competition.distinct_employers": 25}
    assert rate(many, seniority="Senior").rating == "hard_to_fill"
    assert rate(many, seniority="director").rating == "hard_to_fill"
    assert rate(many, seniority="5+ years").rating == "competitive"


def test_senior_lead_and_executive_shares_sum_to_a_high_bar_at_half():
    many = {"competition.distinct_employers": 25}
    shares = {"seniority.senior": 0.3, "seniority.lead": 0.1, "seniority.mid": 0.4}
    assert rate({**many, **shares}).rating == "competitive"
    assert rate({**many, **shares, "seniority.executive": 0.1}).rating == "hard_to_fill"


def named(data, **labels):
    stats, sample = data
    return MarketStats(sample_size=stats.sample_size, stats=[s.model_copy(update={"label": labels.get(s.id, s.label)}) for s in stats.stats]), sample


def recs(data, seniority=None):
    stats, sample = data
    return recommendations(stats, request(seniority), sample)


def title_world(*specs):
    data = world(*((i, n, e) for i, n, e, _ in specs))
    return named(data, **{i: f"{name}: {n} of 99 Postings in the Sample" for i, n, _, name in specs})


def test_a_title_needs_enough_postings_from_enough_employers():
    data = title_world(("titles.variant.a", 10, 1, "Solo Ad"), ("titles.variant.b", 2, 2, "Too Few"), ("titles.variant.c", 3, 2, "Data Engineer"))
    assert recs(data).job_title.title == "Data Engineer"
    assert recs(title_world(("titles.variant.a", 10, 1, "Solo Ad"))).job_title is None


def test_titles_rank_by_employers_then_postings_then_id():
    assert recs(title_world(("titles.variant.a", 30, 3, "A"), ("titles.variant.b", 9, 4, "B"))).job_title.title == "B"
    assert recs(title_world(("titles.variant.a", 8, 4, "A"), ("titles.variant.b", 9, 4, "B"))).job_title.title == "B"
    assert recs(title_world(("titles.variant.b", 8, 4, "B"), ("titles.variant.a", 8, 4, "A"))).job_title.title == "A"


def test_a_title_with_the_requests_level_words_comes_first_and_otherwise_nothing_changes():
    data = title_world(("titles.variant.plain", 20, 9, "Data Engineer"), ("titles.variant.senior", 5, 3, "Senior Data Engineer"))
    picked = recs(data, seniority="sr").job_title
    assert picked.title == "Senior Data Engineer" and "senior level" in picked.reason
    assert picked.stat_ids == ["titles.variant.senior"] and picked.evidence.count == 5
    assert recs(data).job_title.title == "Data Engineer"
    assert recs(data, seniority="lead").job_title.title == "Data Engineer"  # no title holds the level


def pay(group, n=25, low=100.0, mid=120.0, high=150.0, prefix=None):
    p = prefix or f"comp.{group}"
    return [(f"{p}.median", n, 12, mid), (f"{p}.p25", n, 12, low), (f"{p}.p75", n, 12, high)]


def test_the_band_takes_the_first_of_advertised_then_estimated_and_runs_p25_to_p75():
    band = recs(world(*pay("estimated", low=1.0), *pay("advertised", low=117761.0, high=184620.0))).salary_band
    assert (band.low, band.high, band.unit) == (117761.0, 184620.0, "USD/year")
    assert band.stat_ids == ["comp.advertised.p25", "comp.advertised.median", "comp.advertised.p75"]
    assert band.reason == "Middle 50% of 25 advertised figures, at all levels."
    assert recs(world(*pay("estimated"))).salary_band.stat_ids[0] == "comp.estimated.p25"
    assert recs(world(("demand.sample_size", 12, 12))).salary_band is None


def test_estimated_pay_says_it_is_adzunas_estimate_and_federal_says_fixed_tables():
    estimated = recs(world(*pay("estimated", n=100), source=Source.adzuna), seniority="senior").salary_band
    assert estimated.reason == "Middle 50% of 100 Adzuna-estimated figures, at all levels. These are Adzuna's estimates, not pay employers stated."
    federal = recs(world(*pay("federal"), source=Source.usajobs)).salary_band
    assert federal.reason.endswith("at all levels. Federal pay follows fixed tables.")


def test_federal_pay_only_sets_the_band_when_over_half_the_sample_is_usajobs():
    assert recs(world(*pay("federal"), source=Source.adzuna)).salary_band is None


def test_the_band_uses_the_requests_level_slice_within_the_group_or_the_whole_group():
    data = world(*pay("advertised"), *pay("advertised", low=200.0, high=300.0, prefix="comp.advertised.senior"))
    sliced = recs(data, seniority="Senior").salary_band
    assert (sliced.low, sliced.high) == (200.0, 300.0) and "at senior level" in sliced.reason
    assert sliced.stat_ids[0] == "comp.advertised.senior.p25"
    assert recs(data, seniority="mid").salary_band.low == 100.0  # no mid slice: the whole group, at all levels
    assert recs(data).salary_band.low == 100.0
    # A slice in a later group doesn't beat the first group's whole figures.
    later = world(*pay("advertised"), *pay("estimated", prefix="comp.estimated.senior"))
    assert recs(later, seniority="senior").salary_band.stat_ids[0] == "comp.advertised.p25"


def skill_world(*specs, source=Source.usajobs):
    data = world(*((f"skills.{k}.count", n, e) for k, n, e in specs), source=source)
    return named(data, **{f"skills.{k}.count": f"{k.title()}: {n} of 90 extracted Postings, from {e} employers" for k, n, e in specs})


def test_top_skills_are_the_first_five_with_enough_employers_in_stat_order():
    data = skill_world(("python", 20, 10), ("rare", 9, 2), *((f"s{i}", 8, 4) for i in range(5)))
    skills = recs(data).top_skills
    assert skills.skills == ["Python", "S0", "S1", "S2", "S3"]  # "rare" has 2 employers, and the cap is 5
    assert skills.stat_ids[0] == "skills.python.count" and skills.evidence.count == 52
    assert skills.reason.startswith("Asked for by the most employers: Python (20 Postings), S0 (8 Postings)")
    assert "snippets" not in skills.reason


def test_skills_say_they_come_from_snippets_when_an_adzuna_posting_is_in_the_sample():
    assert "Skills come from Adzuna snippets" in recs(skill_world(("python", 20, 10), source=Source.adzuna)).top_skills.reason


def test_each_recommendation_is_none_on_its_own_without_evidence():
    only_skills = recs(skill_world(("python", 20, 10)))
    assert only_skills.job_title is None and only_skills.salary_band is None and only_skills.top_skills
    assert recs(skill_world(("rare", 9, 2))).top_skills is None
    only_pay = recs(world(*pay("advertised")))
    assert only_pay.salary_band and only_pay.job_title is None and only_pay.top_skills is None
