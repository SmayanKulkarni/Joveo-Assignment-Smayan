from enum import StrEnum

from pydantic import Field, model_validator

from talent_scout.kernel.types import Assumption, ClarifyingQuestion, CurrencyCode, Model, SearchPlan, WorkMode


# At their final module path: checkpoints store class paths. The Request & Plan LLD owns these fields.
class RequestDraft(Model):
    """The LLM's reading of the request. Every field may be null, so a vague request never fails validation."""

    role: str | None = Field(description="The job title being hired for, in the user's words; null if not stated.")
    location: str | None = Field(description="Where the hire will work, as the user gave it; null if not stated.")
    country: str | None = Field(
        pattern=r"^[a-z]{2}$",
        description="Lowercase two-letter country code the location implies, e.g. Texas -> us; null if no place implies one.",
    )
    seniority: str | None = Field(description="Seniority level, e.g. junior or senior; null if not stated.")
    employment_type: str | None = Field(description="e.g. full-time, contract; null if not stated.")
    work_mode: WorkMode | None = Field(description="onsite, hybrid or remote; null if not stated.")
    currency: CurrencyCode | None = Field(description="ISO 4217 currency the user wants pay shown in; null if not stated.")
    purpose: str | None = Field(description="Why the user wants this market view; null if not stated.")


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

    @model_validator(mode="after")
    def _needs_payload(self):
        if self.action == PlanAction.edit and self.plan is None:
            raise ValueError("an edit needs the edited plan")
        if self.action == PlanAction.reject and not (self.feedback and self.feedback.strip()):
            raise ValueError("a reject needs feedback")
        return self
