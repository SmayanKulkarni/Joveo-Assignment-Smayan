import asyncio
from datetime import date

import pytest

from talent_scout.analysis.match import compute_matches, default_view, score_posting
from talent_scout.analysis.nodes import _names_to_merge, make_nodes
from talent_scout.analysis.types import EmployerType, Extraction, Level, Requirement, ResumeFacts, ResumeSkill, Seniority, SkillMention
from talent_scout.brief.markdown import PARTIAL_LABEL, REMOTE_LABEL, render_recommendation
from talent_scout.brief.rules import recommendations
from talent_scout.collection.testing import make_deps, posting, state_with
from talent_scout.kernel.types import HiringRequest, MarketStats, Source


def resume(*skills, seniority="senior", years=6) -> ResumeFacts:
    return ResumeFacts(
        roles=[], skills=[ResumeSkill(name=s.lstrip("+"), added=s.startswith("+")) for s in skills],
        seniority=seniority, locations=[], years=years,
    )


def extraction(*skills, seniority="senior", years=None) -> Extraction:
    mentions = [SkillMention(name=n, requirement=Requirement(r)) for n, r in (s.split(":") if ":" in s else (s, "unstated") for s in skills)]
    return Extraction(skills=mentions, seniority=seniority, years_min=years, employer_type=EmployerType.direct, ungrounded=0)


def score(ext, res, aliases=None):
    return score_posting("k", ext, res, aliases or {})


def test_score_weights_must_two_unstated_one_nice_half():
    # 2 + 1 + 0.5 matched of 2 + 1 + 0.5 + 2 = 5.5 total
    m = score(extraction("Python:must", "SQL", "Go:nice", "Rust:must"), resume("Python", "SQL", "Go"))
    assert m.score == round(100 * 3.5 / 5.5) and m.missing == ["Rust"]


def test_the_floor_of_five_stops_a_two_skill_snippet_scoring_100():
    assert score(extraction("Python", "SQL"), resume("Python", "SQL")).score == 40


def test_matching_goes_one_way_only():
    assert [s.resume for s in score(extraction("SQL"), resume("SQL Server")).matched] == ["SQL Server"]
    assert score(extraction("SQL Server"), resume("SQL")).matched == []


def test_aliases_join_spellings_and_both_are_shown_with_the_csm_mark():
    m = score(extraction("Postgres"), resume("+PostgreSQL"), {"postgres": "PostgreSQL"})
    [skill] = m.matched
    assert (skill.posting, skill.resume, skill.added) == ("Postgres", "PostgreSQL", True)


@pytest.mark.parametrize(
    ("posting_level", "resume_level", "expected"),
    [("senior", "senior", Level.fits), ("mid", "senior", Level.fits), ("junior", "senior", Level.fits) if False else ("entry", "senior", Level.far),
     ("lead", "senior", Level.stretch), ("executive", "senior", Level.far), ("unknown", "senior", Level.not_judged)],
)
def test_seniority_level(posting_level, resume_level, expected):
    assert score(extraction("A", seniority=posting_level), resume("A", seniority=resume_level, years=None)).level == expected


@pytest.mark.parametrize(("asked", "has", "expected"), [(5, 6, Level.fits), (7, 6, Level.stretch), (8, 6, Level.stretch), (9, 6, Level.far)])
def test_years_level(asked, has, expected):
    assert score(extraction("A", seniority="unknown", years=asked), resume("A", years=has)).level == expected


def test_the_worse_test_wins_and_unknowns_cost_nothing():
    assert score(extraction("A", seniority="senior", years=12), resume("A", years=6)).level == Level.far
    assert score(extraction("A", seniority="unknown"), resume("A", seniority="unknown")).level == Level.not_judged


def test_ranking_puts_far_last_then_score_matches_newest_and_key():
    sample = [
        posting("a", posted=date(2026, 1, 10)), posting("b", posted=date(2026, 1, 12)),
        posting("c", posted=date(2026, 1, 12)), posting("d"),
    ]
    ext = {
        sample[0].key: extraction("A", "B", "C"),  # 100% but far
        sample[1].key: extraction("A", "B", "C", "D", "E", "F"),
        sample[2].key: extraction("A", "B", "C", "D", "E", "F"),
        sample[3].key: extraction("A", "B", "C", "D", "E", "F"),
    }
    ext[sample[0].key] = extraction("A", "B", "C", "D", "E", "F", seniority="executive")
    matches, unscored = compute_matches(resume("A", "B", "C", "D", "E", "F"), sample, ext, {})
    assert [m.posting_key.split(":")[1] for m in matches] == ["d", "b", "c", "a"] and unscored == 0
    _, unscored = compute_matches(resume("A"), sample, {}, {})
    assert unscored == 4


def test_a_stuffed_posting_scores_only_what_the_resume_has():
    stuffed = extraction(*[f"Skill{i}" for i in range(12)])
    m = score(stuffed, resume("Skill0", "Skill1"))
    assert m.score == round(100 * 2 / 12) and m.score < 40
    assert default_view([m]) == []


def test_the_default_view_needs_two_skills_a_score_of_40_and_caps_at_20():
    good = [score(extraction("A", "B", "C"), resume("A", "B", "C")).model_copy(update={"posting_key": f"k{i}"}) for i in range(25)]
    one = score(extraction("A"), resume("A"))
    assert len(default_view([one, *good])) == 20 and one not in default_view([one, *good])


def test_resume_names_join_the_merge_input_after_the_cut_and_no_resume_changes_nothing():
    ext = {"a": extraction("Python")}
    assert _names_to_merge(ext) == ["python"]
    assert _names_to_merge(ext, resume("Postgres", "Python")) == ["postgres", "python"]


def run_match(state):
    return asyncio.run(make_nodes(make_deps()[0])["match"](state))


def test_the_match_node_covers_no_resume_an_empty_sample_and_a_bug():
    assert run_match(state_with())["matches"] == []
    assert run_match(state_with(resume=resume("A")))["matches"] == []
    p = posting("a")
    state = state_with(resume=resume("A"), postings={p.key: p}, sample=[p.key], extractions={p.key: extraction("A", "B")})
    update = run_match(state)
    assert update["matches"][0].score == 20 and "1 Postings scored" in update["run_log"][-1].message
    # A broken Extraction must not take the Run down, and the Caveat holds nothing of the Resume.
    broken = state.model_copy(update={"skill_aliases": None})
    caveat = run_match(broken)["run_log"][-1]
    assert caveat.kind == "caveat" and caveat.message == "Matches unavailable"


def test_the_recommendation_shows_rows_labels_and_the_rest_behind_a_heading():
    request = HiringRequest(role="Dev", location="Leeds", country="gb", seniority=None, employment_type=None, work_mode=None, currency=None, purpose=None)
    sample = [posting("a", remote=True), posting("b", source=Source.usajobs), posting("c")]
    ext = {sample[0].key: extraction("A", "B", "C"), sample[1].key: extraction("A", "B", "C"), sample[2].key: extraction("A", "X", "Y", "Z")}
    matches, _ = compute_matches(resume("+A", "B", "C"), sample, ext, {})
    recs = recommendations(MarketStats(sample_size=3, stats=[]), request, sample)
    text = render_recommendation(recs, request, sample, matches)
    assert REMOTE_LABEL in text and PARTIAL_LABEL in text and "[added by CSM]" in text
    assert "1. **Data Analyst**" in text and "### The other 1 scored Postings" in text
    nothing = render_recommendation(recs.model_copy(update={"matches_note": "No Posting passed"}), request, sample, [])
    assert "No Posting passed" in nothing
