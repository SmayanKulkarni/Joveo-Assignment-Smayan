import pytest

from talent_scout.analysis.stats import FX_DATE, UNITS_PER_USD, compute_stats
from talent_scout.analysis.types import EmployerType, Extraction, Seniority
from talent_scout.collection.testing import FETCHED_AT, plan, posting, record, request, state_with
from talent_scout.kernel.types import ADZUNA_CURRENCY, PayPeriod, Salary, Source


def paid(prefix: str, n: int, amount: float, *, period="unknown", currency="USD", predicted=False, source=Source.adzuna, upper=None):
    salary = Salary(min=amount, max=upper, currency=currency, period=PayPeriod(period), predicted=predicted)
    return [posting(f"{prefix}{i}", source=source).model_copy(update={"salary": salary}) for i in range(n)]


def state(postings, *, currency=None, country="us", levels=None):
    """Plan country `us` makes USD the Stat currency unless the request names one."""
    extractions = {p.key: Extraction(skills=[], seniority=levels[p.source_id[:-1]] if levels else Seniority.mid, years_min=None, employer_type=EmployerType.direct, ungrounded=0) for p in postings}
    return state_with(
        postings={p.key: p for p in postings}, sample=[p.key for p in postings], extractions=extractions,
        fetches=[record([], fetched_at=FETCHED_AT)], search_plan=plan(country=country),
        hiring_request=request().model_copy(update={"currency": currency}),
    )


def pay(s) -> dict:
    return {st.id: st for st in compute_stats(s)[0].stats if st.id.startswith("comp.")}


def caveats(s, prefix: str) -> list[str]:
    return [c for c in compute_stats(s)[1] if c.startswith(prefix)]


def test_the_table_holds_every_adzuna_currency():
    assert set(UNITS_PER_USD) == set(ADZUNA_CURRENCY.values()) and len(UNITS_PER_USD) == 13
    assert UNITS_PER_USD["USD"] == 1 and FX_DATE


@pytest.mark.parametrize(
    ("period", "amount", "annual"),
    [("hourly", 50, 104000), ("daily", 400, 104000), ("weekly", 2000, 104000), ("biweekly", 4000, 104000),
     ("monthly", 10000, 120000), ("annual", 104000, 104000), ("unknown", 104000, 104000)],
)
def test_each_period_annualises(period, amount, annual):
    got = pay(state(paid("a", 5, amount, period=period)))
    assert got["comp.advertised.median"].value == annual
    assert got["comp.advertised.median"].unit == "USD/year"


def test_a_figure_is_the_midpoint_of_min_and_max_or_the_one_bound():
    assert pay(state(paid("a", 5, 80000, upper=100000)))["comp.advertised.median"].value == 90000
    only_max = [p.model_copy(update={"salary": Salary(min=None, max=70000, currency="USD", period=PayPeriod.annual, predicted=False)}) for p in paid("b", 5, 1)]
    assert pay(state(only_max))["comp.advertised.median"].value == 70000


def test_the_three_groups_never_mix():
    advertised, estimated = paid("a", 5, 100000), paid("e", 5, 50000, predicted=True)
    federal = paid("f", 5, 80000, source=Source.usajobs)
    got = pay(state(advertised + estimated + federal))
    assert got["comp.advertised.median"].value == 100000
    assert got["comp.estimated.median"].value == 50000
    assert got["comp.federal.median"].value == 80000
    assert got["comp.estimated.median"].label == "Adzuna-estimated median pay, 5 Postings, USD/year"
    assert set(got["comp.federal.median"].evidence.posting_keys) == {p.key for p in federal}


def test_quartiles_are_inclusive_and_round_to_whole_units():
    postings = [paid(f"q{i}", 1, v)[0] for i, v in enumerate((10000.4, 20000, 30000, 40000, 50000.6))]
    got = pay(state(postings))
    assert [got[f"comp.advertised.{k}"].value for k in ("p25", "median", "p75")] == [20000, 30000, 40000]
    assert got["comp.advertised.median"].label == "Advertised median pay, 5 Postings, USD/year"


def test_a_figure_of_25_with_an_unknown_period_is_excluded_and_counted():
    low = paid("low", 1, 25)
    s = state(paid("a", 5, 100000) + low)
    got = pay(s)
    assert low[0].key not in got["comp.advertised.median"].evidence.posting_keys and got["comp.advertised.median"].evidence.count == 5
    assert caveats(s, "Implausible pay excluded") == ["Implausible pay excluded: 1 figure with no pay period, too low to be annual pay"]


def test_a_monthly_figure_is_excluded_by_the_sixth_rule_and_a_real_junior_figure_isnt():
    monthly, junior = paid("m", 1, 8000), paid("j", 1, 20000)
    got = pay(state(paid("a", 5, 100000) + monthly + junior))["comp.advertised.median"]
    assert monthly[0].key not in got.evidence.posting_keys and junior[0].key in got.evidence.posting_keys


def test_the_exclusion_rules_only_touch_unknown_periods():
    hourly = paid("h", 5, 25, period="hourly")
    s = state(paid("a", 5, 100000) + hourly)
    assert pay(s)["comp.advertised.median"].evidence.count == 10
    assert not caveats(s, "Implausible pay excluded")


def test_conversion_goes_through_usd_into_the_stat_currency():
    gbp = paid("g", 5, 50000, currency="GBP")
    got = pay(state(gbp))["comp.advertised.median"]
    assert got.value == 66997 and got.label.endswith("USD/year, converted from GBP")
    eur = pay(state(paid("a", 5, 100000), currency="EUR"))["comp.advertised.median"]
    assert eur.value == 89510 and eur.unit == "EUR/year"


def test_the_stat_currency_falls_back_to_the_countrys_when_the_request_has_none_or_one_off_the_table():
    assert pay(state(paid("a", 5, 100000), country="gb"))["comp.advertised.median"].unit == "GBP/year"
    assert pay(state(paid("a", 5, 100000), currency="XYZ", country="gb"))["comp.advertised.median"].unit == "GBP/year"


def test_four_figures_give_no_stats_and_five_do():
    assert not [i for i in pay(state(paid("a", 4, 100000))) if i.startswith("comp.advertised.")]
    assert "comp.advertised.median" in pay(state(paid("a", 5, 100000)))


def test_seniority_slices_need_five_figures_at_the_level_and_exist_for_advertised_and_estimated_only():
    levels = {"s": Seniority.senior, "j": Seniority.entry, "e": Seniority.senior, "f": Seniority.senior}
    advertised = paid("s", 5, 120000) + paid("j", 4, 60000)
    s = state(advertised + paid("e", 5, 90000, predicted=True) + paid("f", 5, 80000, source=Source.usajobs), levels=levels)
    got = pay(s)
    assert got["comp.advertised.senior.median"].value == 120000
    assert got["comp.advertised.senior.median"].label == "Advertised median pay at senior level, 5 Postings, USD/year"
    assert got["comp.estimated.senior.median"].value == 90000
    assert "comp.advertised.entry.median" not in got
    assert not [i for i in got if i.startswith("comp.federal.") and i.count(".") > 2]


def test_shares_count_advertised_and_estimated_over_adzuna_postings_and_federal_is_not_disclosure():
    s = state(paid("a", 2, 100000) + paid("e", 1, 50000, predicted=True) + [posting("none")] + paid("f", 4, 80000, source=Source.usajobs))
    got = pay(s)
    assert got["comp.disclosed_share"].value == 0.5 and got["comp.estimated_share"].value == 0.25
    assert got["comp.disclosed_share"].label == "Adzuna Postings with advertised pay: 50.0% (2 of 4)"
    assert not {"comp.disclosed_share", "comp.estimated_share"} & set(pay(state(paid("f", 5, 80000, source=Source.usajobs))))


# Caveats


def test_pay_is_estimated_fires_only_when_estimated_stats_exist_without_advertised_ones():
    estimated = paid("e", 5, 50000, predicted=True)
    assert len(caveats(state(estimated), "Pay is estimated")) == 1
    assert not caveats(state(estimated + paid("a", 5, 100000)), "Pay is estimated")
    assert not caveats(state(paid("a", 5, 100000)), "Pay is estimated")


def test_too_little_pay_data_fires_only_when_no_group_reached_five_figures():
    assert len(caveats(state(paid("a", 4, 100000) + paid("e", 4, 50000, predicted=True)), "Too little pay data")) == 1
    assert not caveats(state(paid("a", 4, 100000) + paid("e", 5, 50000, predicted=True)), "Too little pay data")


def test_pay_period_assumed_counts_advertised_figures_with_an_unknown_period_only():
    assert caveats(state(paid("a", 5, 100000)), "Pay period assumed") == ["Pay period assumed: treated as annual for 5 advertised figures with no pay period"]
    assert not caveats(state(paid("a", 5, 100000, period="annual")), "Pay period assumed")
    assert not caveats(state(paid("e", 5, 100000, predicted=True)), "Pay period assumed")


def test_pay_converted_fires_when_a_posting_is_paid_in_another_currency():
    s = state(paid("g", 5, 50000, currency="GBP"))
    assert caveats(s, "Pay converted") == [f"Pay converted: 5 Postings paid in another currency, converted to USD at ECB rates of {FX_DATE}"]
    assert not caveats(state(paid("a", 5, 100000)), "Pay converted")


def test_currency_unavailable_fires_when_the_requested_currency_isnt_in_the_table():
    postings = paid("a", 5, 100000)
    assert caveats(state(postings, currency="XYZ"), "Currency unavailable") == ["Currency unavailable: XYZ has no exchange rate, so pay is shown in USD"]
    assert not caveats(state(postings, currency="EUR"), "Currency unavailable")
    assert not caveats(state(postings), "Currency unavailable")
