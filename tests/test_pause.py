import pytest
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pydantic import TypeAdapter, ValidationError

from talent_scout.collection.testing import posting, record
from talent_scout.collection.types import LowDataAnswer, LowDataPayload
from talent_scout.kernel.types import ClarifyingQuestion, RequestField, SearchPlan, WorkMode
from talent_scout.request_plan.types import (
    ClarifyAnswer,
    ClarifyPayload,
    PlanAction,
    PlanReviewAnswer,
    PlanReviewPayload,
    RequestDraft,
)
from talent_scout.runtime.pause import (
    ALLOWED_MSGPACK,
    ANSWERS,
    ClarifyPause,
    LowDataPause,
    Pause,
    PlanReviewPause,
)

QUESTION = ClarifyingQuestion(about=RequestField.role, text="Which engineer?", options=["Software"], answer=None)
PLAN = SearchPlan(
    titles=["Engineer"], country="us", location="Texas", radius_km=0,
    max_days_old=30, target_postings=50, category=None,
)
LOW_DATA = LowDataPayload(
    count=3, target=50, attempts=2, plans=[PLAN], fetched=12, rejected=9, calls_left=4, blocked=None,
)
PAUSES = [
    ClarifyPause(payload=ClarifyPayload(questions=[QUESTION])),
    PlanReviewPause(payload=PlanReviewPayload(plan=PLAN, assumptions=[])),
    LowDataPause(payload=LOW_DATA),
]
DRAFT = RequestDraft(
    role="Engineer", location="Texas", country="us", seniority=None, employment_type=None,
    work_mode=WorkMode.remote, currency="USD", purpose=None,
)
VALUES = [
    *PAUSES,
    ClarifyAnswer(answers=["Software"]),
    PlanReviewAnswer(action=PlanAction.edit, plan=PLAN, feedback=None),
    LowDataAnswer(action="continue"),
    LowDataAnswer(action="broaden", guidance="Try wider"),
    # Source-keyed dicts and enums inside a record must survive too.
    record([posting("1")]),
    DRAFT,
]


def roundtrip(serde: JsonPlusSerializer, value):
    return serde.loads_typed(serde.dumps_typed(value))


@pytest.mark.parametrize("value", VALUES, ids=lambda v: type(v).__name__)
def test_value_survives_the_allowlisted_serializer(value):
    assert roundtrip(JsonPlusSerializer(allowed_msgpack_modules=ALLOWED_MSGPACK), value) == value


def test_strict_mode_blocks_a_class_off_the_allowlist():
    # Proves the package __init__ really turned strict mode on, or the test above means nothing.
    assert not isinstance(roundtrip(JsonPlusSerializer(), PAUSES[0]), ClarifyPause)


def test_pause_union_picks_its_class_by_kind():
    pause = TypeAdapter(Pause).validate_python({"kind": "low_data_review", "payload": LOW_DATA.model_dump()})
    assert pause == LowDataPause(payload=LOW_DATA)


@pytest.mark.parametrize(
    "bad",
    [
        {"action": "edit", "plan": None, "feedback": None},
        {"action": "reject", "plan": None, "feedback": None},
        {"action": "reject", "plan": None, "feedback": "  "},
    ],
)
def test_plan_review_answer_needs_its_payload(bad):
    with pytest.raises(ValidationError):
        PlanReviewAnswer.model_validate(bad)


@pytest.mark.parametrize(
    "kind, bad",
    [
        ("clarify", {"answers": "not a list"}),
        ("plan_review", {"action": "maybe", "plan": None, "feedback": None}),
        ("low_data_review", {"action": "maybe"}),
    ],
)
def test_answer_table_rejects_a_bad_answer(kind, bad):
    with pytest.raises(ValidationError):
        ANSWERS[kind].model_validate(bad)
