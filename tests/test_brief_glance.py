import pytest

from test_brief_render import run, sample_state
from talent_scout.brief.glance import MAX_NOTES, NO_AREA, glance
from talent_scout.collection.testing import plan
from talent_scout.kernel.state import LogKind, log_entry

# One Caveat per note, worded as the code writes them.
CAVEATS = {
    "Places not searched: Thane": "We couldn't search Thane.",
    "Old data: 9 of 12 Postings are over 30 days old": "Most of these postings are over 30 days old.",
    "Mostly federal: 9 of 12 Postings are from USAJOBS": "Most of these postings are US federal jobs.",
    "One source failed: usajobs": "One job source didn't answer, so this rests on the other.",
}


def brief_with(n=25, edits=None, **notes):
    brief = run(sample_state(n, edits))["brief"]
    return brief.model_copy(update={"run_notes": brief.run_notes.model_copy(update=notes)})


def sample(edits=None, n=25):
    state = sample_state(n, edits)
    return state, [state.postings[k] for k in state.sample]


@pytest.mark.parametrize("caveat, note", CAVEATS.items())
def test_each_caveat_note_reads_on_a_real_brief(caveat, note):
    brief = brief_with(caveats=[caveat])
    assert note in glance(brief, sample()[1]).reader_notes


def test_notes_follow_the_lld_order_and_stop_at_two():
    first = plan(locations=["Mumbai"])
    brief = brief_with(
        earlier_plans=[first], final_plan=plan(locations=[], target_postings=100),
        caveats=["Places not searched: Thane", "Old data: 9 of 12"],
    )

    notes = glance(brief, sample()[1]).reader_notes

    assert len(notes) == MAX_NOTES
    assert notes[0] == "We searched the whole country, not only Mumbai."
    assert notes[1] == "We couldn't search Thane."


def test_a_thin_sample_and_a_widened_search_come_after_the_place_notes():
    brief = brief_with(earlier_plans=[plan()], final_plan=plan(target_postings=100))

    assert glance(brief, sample()[1]).reader_notes == [
        "Only 25 postings against the 100 we aimed for, so treat this as a rough guide.",
        "We widened the search to find enough postings.",
    ]


def test_every_caveat_stays_in_the_markdown():
    state = sample_state().model_copy(update={"run_log": [log_entry("collect", LogKind.caveat, "Old data: 9 of 12")]})
    assert "Old data: 9 of 12" in run(state)["brief_markdown"]


def regions(*groups):
    return {i: {"region": r} for i, r in enumerate(groups)}


def test_places_strip_what_all_share_and_a_country_only_region_is_area_not_given():
    edits = regions(*[("India", "Maharashtra", "Mumbai")] * 12, *[("India", "Maharashtra", "Thane")] * 8, *[("India",)] * 5)
    chart = glance(brief_with(), sample(edits)[1]).places

    assert [(r.label, r.count) for r in chart.rows] == [("Mumbai", 12), ("Thane", 8), (NO_AREA, 5)]


def test_places_keep_six_then_count_the_rest_and_hide_under_two_groups():
    many = regions(*[("India", "MH", f"Town {i % 8}") for i in range(25)])
    rows = glance(brief_with(), sample(many)[1]).places.rows
    assert len(rows) == 7 and rows[-1].label == "2 other places"

    one = regions(*[("India", "MH", "Pune")] * 25)
    assert glance(brief_with(), sample(one)[1]).places is None


def test_skills_only_one_employer_asks_for_are_left_out_and_pay_hides_without_a_band():
    brief = brief_with()
    solo = brief.model_copy(update={"recommendations": brief.recommendations.model_copy(update={"salary_band": None})})
    g = glance(solo, sample()[1])

    assert g.pay is None
    assert g.skills is None or all(len({k.split(":")[1] for k in r.evidence.posting_keys}) > 1 for r in g.skills.rows)


def test_employer_rows_equal_the_stats():
    brief = brief_with()
    chart = glance(brief, sample()[1]).employers
    by_id = {s.id: s for s in brief.stats.stats}

    assert chart and all(r.count == by_id[r.stat_ids[0]].evidence.count for r in chart.rows)


def test_skill_rows_show_required_counts_and_drop_one_employer_skills():
    from talent_scout.kernel.types import Dimension, Evidence, MarketStats, Stat

    def stat(id, keys, label):
        return Stat(id=id, dimension=Dimension.skills, label=label, value=len(keys), unit="postings", evidence=Evidence(posting_keys=keys))

    brief = brief_with()
    stats = [
        stat("skills.sql.count", ["adzuna:0", "adzuna:1", "adzuna:2"], "SQL: 3 of 9 extracted Postings, from 3 employers"),
        stat("skills.sql.must", ["adzuna:0"], "SQL: required in 1 of 9 extracted Postings"),
        stat("skills.solo.count", ["adzuna:4"], "Solo: 1 of 9 extracted Postings, from 1 employer"),
    ]
    chart = glance(brief.model_copy(update={"stats": MarketStats(sample_size=25, stats=stats)}), sample()[1]).skills

    assert [(r.label, r.count, r.required) for r in chart.rows] == [("SQL", 3, 1)]
    assert "9 postings" in chart.caption
