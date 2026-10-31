from typing import Annotated, Literal

from pydantic import Field

from talent_scout.collection.types import FetchRecord, LowDataAnswer, LowDataPayload
from talent_scout.gateway.types import CacheStatus
from talent_scout.kernel.types import Model, PayPeriod, RequestField, Source, WorkMode
from talent_scout.request_plan.types import (
    ClarifyAnswer,
    ClarifyPayload,
    PlanAction,
    PlanReviewAnswer,
    PlanReviewPayload,
    RequestDraft,
)


class ClarifyPause(Model):
    kind: Literal["clarify"] = "clarify"
    payload: ClarifyPayload


class PlanReviewPause(Model):
    kind: Literal["plan_review"] = "plan_review"
    payload: PlanReviewPayload


class LowDataPause(Model):
    kind: Literal["low_data_review"] = "low_data_review"
    payload: LowDataPayload


Pause = Annotated[ClarifyPause | PlanReviewPause | LowDataPause, Field(discriminator="kind")]
ANSWERS = {"clarify": ClarifyAnswer, "plan_review": PlanReviewAnswer, "low_data_review": LowDataAnswer}

# Nested models are rebuilt from the outer class's fields, but nested enums keep their own
# class path, and an unlisted one logs a "blocked" warning on every load.
ALLOWED_MSGPACK = [
    (cls.__module__, cls.__name__)
    for cls in (
        ClarifyPause, PlanReviewPause, LowDataPause, *ANSWERS.values(), PlanAction, RequestField, RequestDraft, WorkMode,
        FetchRecord, CacheStatus, Source, PayPeriod,
    )
]
