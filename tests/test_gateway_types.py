import pytest
from pydantic import ValidationError

from talent_scout.gateway.types import ATTRIBUTION, Fetch
from talent_scout.kernel.types import Source


def make_fetch(**kw):
    base = dict(title="data engineer", country="us", location="", radius_km=0, max_days_old=30, category=None)
    return Fetch(**{**base, **kw})


def test_text_fields_are_lowercased_stripped_and_collapsed():
    f = make_fetch(title="  Senior   DATA\tEngineer ", location=" New  York ", category=" IT-Jobs ")
    assert (f.title, f.location, f.category) == ("senior data engineer", "new york", "it-jobs")


def test_equal_fetches_dump_equal_json():
    a = make_fetch(title="Data  Engineer", location="LONDON")
    b = make_fetch(title="data engineer", location="london")
    assert a == b
    assert a.model_dump_json() == b.model_dump_json()


def test_blank_title_is_rejected():
    with pytest.raises(ValidationError):
        make_fetch(title="   ")


def test_country_outside_adzuna_table_is_rejected():
    with pytest.raises(ValidationError):
        make_fetch(country="jp")


@pytest.mark.parametrize("bad", [dict(radius_km=-1), dict(max_days_old=0), dict(page=0)])
def test_numeric_bounds_are_rejected(bad):
    with pytest.raises(ValidationError):
        make_fetch(**bad)


def test_adzuna_attribution_is_exported():
    assert ATTRIBUTION[Source.adzuna] == "The Adzuna API"
