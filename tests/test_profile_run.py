from datetime import date

from talent_scout.brief.rules import compared_line
from talent_scout.kernel.state import State
from talent_scout.kernel.testing import fake_classifier
from talent_scout.kernel.types import Earlier, RequestField, RunProfile
from talent_scout.request_plan.nodes import _plan_input, make_nodes, profile_fields
from talent_scout.request_plan.types import PROFILE_REASON
from test_request_plan import draft, make_deps, question_json, run

BLANK = dict(role=None, location=None, country=None)
PROFILE = RunProfile(
    values={"role": "Data Engineer", "seniority": "senior", "places": ["Austin"], "country": "us"}, titles=["Data Engineer", "ETL Developer"],
)


def intake_then_clarity(profile, request_text="hiring", **fields):
    # Every field the classifier is asked about reads as ambiguous, so only a skipped one stays quiet.
    deps = make_deps(
        cheap=[draft(**{**BLANK, **fields}).model_dump_json(), question_json(), question_json()],
        classifier=fake_classifier({"role": 0.9, "location": 0.9, "seniority": 0.9}),
    )[0]
    nodes = make_nodes(deps)
    state = State(request_text=request_text, profile=profile)
    state = state.model_copy(update=run(nodes["intake"], state))
    return state, run(nodes["clarity_check"], state)


def test_a_second_run_asks_fewer_questions_and_its_plan_shows_the_hints():
    _, first = intake_then_clarity(None)
    state, second = intake_then_clarity(PROFILE)
    assert len(first["questions"]) == 2 and "questions" not in second
    assert {a.about: a.reason for a in second["assumptions"]} == {
        RequestField.role: PROFILE_REASON, RequestField.seniority: PROFILE_REASON, RequestField.location: PROFILE_REASON,
    }
    assert second["hiring_request"].country == "us"

    planned = state.model_copy(update=second)
    assert "- ETL Developer" in _plan_input(planned) and "hints, not requirements" in _plan_input(planned)
    assert profile_fields(planned) == ["role", "seniority", "location", "titles"]


def test_a_typed_value_is_never_overridden():
    state, update = intake_then_clarity(PROFILE, request_text="Data Analyst in Oslo", role="Data Analyst", location="Oslo", country="no")
    assert state.request_draft.role == "Data Analyst" and state.request_draft.location == "Oslo"
    assert RequestField.role not in {a.about for a in update.get("assumptions", [])}
    assert RequestField.location not in {a.about for a in update.get("assumptions", [])}


def test_the_recommendation_compares_with_the_newest_earlier_run_of_the_same_market():
    from test_brief_writer import REQUEST, stats
    earlier = lambda day, role, pay: Earlier(
        thread_id=f"t{day}", date=date(2026, 1, day), role=role, country=REQUEST.country, sample_size=40, median_pay=pay, currency="USD",
    )
    base = State(request_text="x", hiring_request=REQUEST, stats=stats())
    assert compared_line(base) is None
    other = base.model_copy(update={"profile": RunProfile(earlier=[earlier(3, "Chef", 1.0)])})
    assert compared_line(other) is None

    # Newest first, so the first of the same market wins; the role is compared folded.
    same = base.model_copy(update={"profile": RunProfile(earlier=[earlier(3, "Chef", 1.0), earlier(2, " data  ENGINEER", 120000.0), earlier(1, "Data Engineer", 1.0)])})
    assert compared_line(same) == (
        "Compared with the Run of 2026-01-02: median Advertised pay 120,000 USD then and 134,000 USD now; Sample size 40 then and 125 now."
    )
