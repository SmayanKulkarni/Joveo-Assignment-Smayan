from datetime import date

from talent_scout.gateway.coalesce import coalesce
from talent_scout.kernel.types import Posting, Salary, Source

SNIPPET = "We are hiring a data engineer to build pipelines on the cloud platform and own"


def salary(amount, predicted=False):
    return Salary(min=amount, max=amount, currency="USD", period="unknown", predicted=predicted)


def posting(id, *, source=Source.adzuna, title="Data Engineer", company="Acme", description=SNIPPET,
            posted=date(2026, 10, 1), pay=None):
    return Posting(
        source=source, source_id=id, title=title, company=company, location="X", region=("US",), domain=None,
        posted_at=posted, closes_at=None, description=description, url="u", salary=pay,
    )


def test_same_title_employer_and_description_collapse_with_merged_filled():
    a, b, c = posting("1"), posting("2"), posting("3")
    kept, merged = coalesce([a, b, c])
    assert [p.key for p in kept] == ["adzuna:1"]
    assert merged == {"adzuna:1": ["adzuna:2", "adzuna:3"]}


def test_title_and_employer_compare_normalised():
    kept, _ = coalesce([posting("1"), posting("2", title="data  ENGINEER", company="ACME.")])
    assert len(kept) == 1


def test_truncated_description_is_a_prefix_of_the_full_one():
    full = SNIPPET + " the whole team across several regions"
    cut = SNIPPET[:-2] + "…"  # ends mid-word, as Adzuna snippets do
    kept, merged = coalesce([posting("1", description=full), posting("2", description=cut)])
    assert len(kept) == 1 and "adzuna:2" in sum(merged.values(), [])


def test_different_descriptions_stay_apart():
    kept, merged = coalesce([posting("1"), posting("2", description="A different requisition entirely")])
    assert len(kept) == 2 and merged == {}


def test_different_title_or_employer_stays_apart():
    kept, _ = coalesce([posting("1"), posting("2", title="Data Engineer 4"), posting("3", company="Other")])
    assert len(kept) == 3


def test_salary_must_match_unless_either_is_predicted():
    assert len(coalesce([posting("1", pay=salary(100)), posting("2", pay=salary(200))])[0]) == 2
    assert len(coalesce([posting("1", pay=salary(100)), posting("2", pay=salary(200, predicted=True))])[0]) == 1
    assert len(coalesce([posting("1", pay=salary(100, True)), posting("2", pay=salary(200, True))])[0]) == 1


def test_survivor_is_usajobs_then_newest_then_lowest_key():
    old, new = posting("1", posted=date(2026, 9, 1)), posting("2", posted=date(2026, 10, 1))
    gov = posting("9", source=Source.usajobs, posted=date(2026, 8, 1))
    assert coalesce([old, new])[0] == [new]
    assert coalesce([old, new, gov])[0] == [gov]
    tie_a, tie_b = posting("5"), posting("4")
    assert coalesce([tie_a, tie_b])[0] == [tie_b]


def test_survivors_keep_input_order():
    a, b = posting("1", title="Alpha"), posting("2", title="Beta")
    assert coalesce([b, a])[0] == [b, a]
