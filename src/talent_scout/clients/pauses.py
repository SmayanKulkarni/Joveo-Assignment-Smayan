from talent_scout.collection.types import LowDataPayload
from talent_scout.kernel.types import SearchPlan
from talent_scout.request_plan.types import ClarifyPayload, PlanReviewPayload
from talent_scout.runtime.pause import Pause


def _clarify(payload: ClarifyPayload) -> str:
    lines = ["Clarifying questions"]
    for number, question in enumerate(payload.questions, 1):
        lines.append(f"{number}. {question.text}")
        lines.extend(f"   [{n}] {option}" for n, option in enumerate(question.options, 1))
    return "\n".join(lines)


def render_plan(plan: SearchPlan) -> str:
    lines = ["Search Plan"]
    for name, value in plan.model_dump().items():
        shown = ", ".join(value) if isinstance(value, list) else "none" if value is None else value
        lines.append(f"  {name}: {shown}")
    return "\n".join(lines)


def _plan_review(payload: PlanReviewPayload) -> str:
    lines = [render_plan(payload.plan)]
    if payload.assumptions:
        lines.append("Assumptions")
        lines.extend(f"  {a.about}: {a.value} ({a.reason})" for a in payload.assumptions)
    return "\n".join(lines)


def _low_data(payload: LowDataPayload) -> str:
    return f"Only {payload.count} relevant Postings found, the target is {payload.target}."


def render_pause(pause: Pause) -> str:
    """Plain text of a Pause, shared by every client."""
    match pause.kind:
        case "clarify":
            return _clarify(pause.payload)
        case "plan_review":
            return _plan_review(pause.payload)
        case "low_data_review":
            return _low_data(pause.payload)
