import pytest
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pydantic import TypeAdapter, ValidationError

from talent_scout.collection.types import LowDataAnswer, LowDataPayload
from talent_scout.kernel.types import ClarifyingQuestion, RequestField, SearchPlan
from talent_scout.request_plan.types import (
    ClarifyAnswer,
    ClarifyPayload,
    PlanAction,
    PlanReviewAnswer,
    PlanReviewPayload,
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
PAUSES = [
    ClarifyPause(payload=ClarifyPayload(questions=[QUESTION])),
    PlanReviewPause(payload=PlanReviewPayload(plan=PLAN, assumptions=[])),
    LowDataPause(payload=LowDataPayload(count=3, target=50)),
]
VALUES = [
    *PAUSES,
    ClarifyAnswer(answers=["Software"]),
    PlanReviewAnswer(action=PlanAction.edit, plan=PLAN, feedback=None),
    LowDataAnswer(action="continue"),
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
    pause = TypeAdapter(Pause).validate_python({"kind": "low_data_review", "payload": {"count": 1, "target": 2}})
    assert pause == LowDataPause(payload=LowDataPayload(count=1, target=2))


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
