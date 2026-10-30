from enum import StrEnum

from talent_scout.kernel.types import Assumption, ClarifyingQuestion, Model, SearchPlan


# At their final module path: checkpoints store class paths. The Request & Plan LLD owns these fields.
class PlanAction(StrEnum):
    approve = "approve"
    edit = "edit"
    reject = "reject"
    abort = "abort"


class ClarifyPayload(Model):
    questions: list[ClarifyingQuestion]


class ClarifyAnswer(Model):
    answers: list[str]


class PlanReviewPayload(Model):
    plan: SearchPlan
    assumptions: list[Assumption]


class PlanReviewAnswer(Model):
    action: PlanAction
    plan: SearchPlan | None
    feedback: str | None
