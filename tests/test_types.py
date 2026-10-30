from datetime import date

import pytest
from pydantic import ValidationError

from talent_scout.gateway.usajobs import DOMAINS
from talent_scout.kernel.types import (
    ADZUNA_CATEGORIES,
    Dimension,
    Evidence,
    HiringRequest,
    MarketStats,
    PayPeriod,
    Posting,
    Salary,
    SearchPlan,
    Source,
    Stat,
)


def salary(**over):
    return Salary(**{"min": 10, "max": 20, "currency": "USD", "period": PayPeriod.annual, "predicted": False, **over})


def stat(id="comp.median"):
    return Stat(id=id, dimension=Dimension.compensation, label="l", value=1.0, unit=None, evidence=Evidence(posting_keys=[]))


def plan(**over):
    return SearchPlan(
        **{"titles": ["a"], "country": "us", "location": "x", "radius_km": 0, "max_days_old": 1,
           "target_postings": 20, "category": None, **over}
    )


def request(**over):
    return HiringRequest(
        **{"role": "r", "location": "l", "country": "us", "seniority": None, "employment_type": None,
           "work_mode": None, "currency": None, "purpose": None, **over}
    )


def test_posting_key():
    p = Posting(source=Source.adzuna, source_id="42", title="t", company=None, location="l", region=("us",),
                domain=None, posted_at=date(2026, 1, 1), closes_at=None, description="d", url="u", salary=None)
    assert p.key == "adzuna:42"


@pytest.mark.parametrize(
    "bad", [{"min": None, "max": None}, {"min": 30, "max": 20}, {"currency": "usd"}, {"currency": "US"}]
)
def test_salary_rejects(bad):
    with pytest.raises(ValidationError):
        salary(**bad)


def test_salary_accepts_one_bound():
    assert salary(min=None).max == 20


def test_evidence_sorts_dedupes_and_counts():
    e = Evidence(posting_keys=["b:2", "a:1", "b:2"])
    assert e.posting_keys == ["a:1", "b:2"]
    assert e.count == 2


def test_market_stats_reject_duplicate_ids():
    with pytest.raises(ValidationError, match="comp.median"):
        MarketStats(sample_size=2, stats=[stat(), stat()])


@pytest.mark.parametrize(
    "bad",
    [
        {"titles": []}, {"titles": list("abcde")},
        {"country": "USA"}, {"country": "US"}, {"country": "jp"},
        {"radius_km": -1}, {"radius_km": 101},
        {"max_days_old": 0}, {"max_days_old": 61},
        {"target_postings": 19}, {"target_postings": 201},
        {"category": "basket-weaving-jobs"},
    ],
)
def test_search_plan_rejects(bad):
    with pytest.raises(ValidationError):
        plan(**bad)


@pytest.mark.parametrize(
    "edge", [{"titles": list("abcd")}, {"radius_km": 100}, {"max_days_old": 60}, {"target_postings": 200}, {"category": "it-jobs"}]
)
def test_search_plan_accepts_the_limits(edge):
    plan(**edge)


def test_adzuna_categories_match_the_usajobs_domains():
    assert ADZUNA_CATEGORIES == {tag for tag in DOMAINS if tag}


@pytest.mark.parametrize("bad", [{"role": "  "}, {"location": ""}, {"country": "jp"}, {"country": "US"}])
def test_hiring_request_rejects(bad):
    with pytest.raises(ValidationError):
        request(**bad)
