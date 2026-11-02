import asyncio

from langchain_typesafe import Noul
from langgraph.graph import END
from langgraph.types import interrupt
from pydantic import Field

from talent_scout.kernel.jev import Judgement
from talent_scout.kernel.state import LogKind, RunLogEntry, State, log, log_entry
from talent_scout.kernel.text import fold
from talent_scout.kernel.types import (
    ADZUNA_CURRENCY,
    Assumption,
    ClarifyingQuestion,
    HiringRequest,
    Model,
    RequestField,
    SearchPlan,
    Source,
    WorkMode,
)
from talent_scout.request_plan.prompts import INTAKE_SYSTEM, JEV_QUESTIONS, PLAN_SYSTEM, PROBLEMS, QUESTION_SYSTEM
from talent_scout.request_plan.types import (
    PROFILE_REASON,
    ClarifyPayload,
    PlanAction,
    PlanReviewPayload,
    RequestDraft,
)
from talent_scout.runtime.deps import Deps, Node, Router
from talent_scout.runtime.pause import ClarifyPause, PlanReviewPause

MAX_ASKS = 2  # a field is asked twice, then settled


class QuestionDraft(Model):
    # Private to this stage: code sets `about` and `answer`, because the LLM shouldn't choose either.
    text: str = Field(description="One short question for the user.")
    options: list[str] = Field(max_length=4, description="Up to 4 suggested answers; empty if open-ended.")


def _blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _answered(state: State) -> list[ClarifyingQuestion]:
    # A blank answer carries no information, so it never reaches a prompt.
    return [q for q in state.questions if not _blank(q.answer)]


def _flag_missing(draft: RequestDraft) -> dict[RequestField, str]:
    """What is plainly wrong with the draft. Country problems fold into `location`, the field the user can answer."""
    flags = {}
    if _blank(draft.role):
        flags[RequestField.role] = "missing"
    if draft.country is not None and draft.country not in ADZUNA_CURRENCY:
        flags[RequestField.location] = "unsupported_country"
    elif _blank(draft.location) or draft.country is None:
        flags[RequestField.location] = "missing"
    return flags


def _finish(
    draft: RequestDraft, settled: dict[RequestField, str], default_country: str
) -> tuple[HiringRequest | None, list[Assumption], str | None]:
    """Turn the draft into a final request, settling fields that hit the ask cap. The last item is an abort reason."""
    location, country = draft.location, draft.country
    assumptions = []
    for field, kind in settled.items():
        if kind == "unsupported_country":
            return None, [], f"no source has job data for country '{draft.country}'"
        if field == RequestField.role and kind == "missing":
            return None, [], "no role to search for"
        if kind == "missing":
            # A request with no usable place is searched country-wide; location must still be non-blank.
            location = country = default_country
            assumptions.append(Assumption(
                about=field, value=f"{default_country} (country-wide)",
                reason="no usable location after two questions",
            ))
        else:
            assumptions.append(Assumption(
                about=field, value=getattr(draft, field.value),
                reason="still ambiguous after two questions, so it is used as given",
            ))
    request = HiringRequest(
        role=draft.role, location=location, country=country, seniority=draft.seniority,
        employment_type=draft.employment_type, work_mode=draft.work_mode,
        currency=draft.currency, purpose=draft.purpose,
    )
    return request, assumptions, None


def _resume_facts(state: State) -> dict[RequestField, str]:
    """What the Resume offers for the fields it can fill. Nothing else of it reaches a prompt here."""
    resume = state.resume
    if resume is None:
        return {}
    facts = {
        RequestField.role: resume.latest_title,
        RequestField.seniority: resume.seniority.value if resume.seniority.value != "unknown" else None,
        RequestField.location: ", ".join(resume.locations) or None,
    }
    return {field: value for field, value in facts.items() if value}


def _profile_facts(state: State) -> dict[RequestField, str]:
    """What the Customer Profile offers for the fields a request can leave empty."""
    values = state.profile.values if state.profile else {}
    facts = {field: values.get(field.value) for field in (
        RequestField.role, RequestField.seniority, RequestField.employment_type, RequestField.work_mode, RequestField.currency,
    )}
    facts[RequestField.location] = ", ".join(values.get("places", []))
    return {field: value for field, value in facts.items() if value}


def _fill_from_profile(state: State, draft: RequestDraft) -> RequestDraft:
    """Code fills only what the model left empty, so nothing typed or taken from the Resume is overridden."""
    update = {field.value: value for field, value in _profile_facts(state).items() if _blank(getattr(draft, field.value))}
    if "work_mode" in update:
        update["work_mode"] = WorkMode(update["work_mode"])
    # A place and its country go together: a country beside a typed place could contradict it.
    if "location" in update and draft.country is None:
        update["country"] = state.profile.values.get("country")
    return draft.model_copy(update=update)


def _intake_input(state: State) -> str:
    lines = [f"Request: {state.request_text}"]
    answered = _answered(state)
    if answered:
        lines += ["", "Answers to earlier questions:", *(f"- {q.text} -> {q.answer}" for q in answered)]
    if facts := _resume_facts(state):
        lines += [
            "", "The Customer's Resume offers these values. Use one only for a field the request and answers leave empty:",
            *(f"- {field.value}: {value}" for field, value in facts.items()),
        ]
    return "\n".join(lines)


def _from_resume(state: State, draft: RequestDraft, settled: list[Assumption]) -> list[Assumption]:
    """A field the draft holds that the CSM never typed can only have come from the Resume, so it is shown as an Assumption."""
    typed = fold(" ".join([state.request_text, *(q.answer for q in _answered(state))]))
    taken = {a.about for a in settled}
    return [
        Assumption(about=field, value=value, reason=f"from the Resume uploaded {state.resume_uploaded}")
        for field in _resume_facts(state)
        if field not in taken and (value := getattr(draft, field.value)) and fold(value) not in typed
    ]


def _from_profile(state: State, draft: RequestDraft, claimed: set[RequestField]) -> list[Assumption]:
    """A field the draft holds with the profile's own value, that was neither typed nor the Resume's, was filled from the profile."""
    typed = fold(" ".join([state.request_text, *(q.answer for q in _answered(state))]))
    return [
        Assumption(about=field, value=value, reason=PROFILE_REASON)
        for field, value in _profile_facts(state).items()
        if field not in claimed and fold(str(getattr(draft, field.value) or "")) == fold(value) and fold(value) not in typed
    ]


def profile_fields(state: State) -> list[str]:
    """What this Run took from the Customer Profile: the fields filled, and "titles" when hints went to the plan."""
    fields = [a.about.value for a in state.assumptions if a.reason == PROFILE_REASON]
    return [*fields, *(["titles"] if state.profile and state.profile.titles else [])]


def _question_input(state: State, draft: RequestDraft, field: RequestField, kind: str) -> str:
    lines = [
        f"Request: {state.request_text}",
        f"Draft: {draft.model_dump_json()}",
        f"Field to ask about: {field.value}",
        f"Problem: {PROBLEMS[kind]}",
    ]
    earlier = [q for q in state.questions if q.about == field]
    if earlier:
        lines += ["Earlier questions about this field:", *(f"- {q.text} (answer: {q.answer or 'blank'})" for q in earlier)]
    return "\n".join(lines)


def _plan_input(state: State) -> str:
    lines = [f"Hiring request: {state.hiring_request.model_dump_json()}"]
    if state.assumptions:
        lines += ["Assumptions:", *(f"- {a.about.value}: {a.value} ({a.reason})" for a in state.assumptions)]
    if state.plan_decision == PlanAction.reject and state.search_plan:
        lines += [f"Previous plan: {state.search_plan.model_dump_json()}", f"Feedback: {state.plan_feedback}"]
    if state.profile and state.profile.titles:
        lines += ["Titles that found enough Postings for this Customer before (hints, not requirements):", *(f"- {t}" for t in state.profile.titles)]
    return "\n".join(lines)


def _caveats(judged: dict[RequestField, Judgement]) -> list[RunLogEntry]:
    # Judgements from one call share their source and truncation, so one entry each is enough.
    caveats = []
    if any(j.source == "llm_fallback" for j in judged.values()):
        caveats.append(log_entry("clarity_check", LogKind.caveat, "Ambiguity of the request was judged by the LLM fallback, not Jev"))
    if any(j.truncated for j in judged.values()):
        caveats.append(log_entry("clarity_check", LogKind.caveat, "The request was shortened to fit Jev, so ambiguity may be misjudged"))
    return caveats


def make_nodes(deps: Deps) -> dict[str, Node]:
    intake_chain = deps.tiers.structured("cheap", RequestDraft, system=INTAKE_SYSTEM, name="intake")
    question_chain = deps.tiers.structured("cheap", QuestionDraft, system=QUESTION_SYSTEM, name="question")
    plan_chain = deps.tiers.structured("strong", SearchPlan, system=PLAN_SYSTEM, name="plan")

    async def intake(state: State) -> dict:
        draft = _fill_from_profile(state, await intake_chain.ainvoke(_intake_input(state)))
        return {
            "request_draft": draft,
            **log(state, "intake", LogKind.note, "parsed request", **draft.model_dump(mode="json")),
        }

    async def judge(state: State, draft: RequestDraft, skip: set[RequestField]) -> dict[RequestField, Judgement]:
        # Only fields that exist and aren't already flagged; a missing seniority is not ambiguous.
        fields = [RequestField.role, RequestField.location]
        if not _blank(draft.seniority):
            fields.append(RequestField.seniority)
        fields = [f for f in fields if f not in skip]
        if not fields:
            return {}
        seen = {
            "request": state.request_text,
            "draft": draft.model_dump(mode="json"),
            "answers": [{"about": q.about.value, "question": q.text, "answer": q.answer} for q in _answered(state)],
        }
        questions = {f.value: Noul(instructions=JEV_QUESTIONS[f.value]) for f in fields}
        result = await deps.jev.judge("clarity", seen, questions)
        return {RequestField(k): j for k, j in result.items()}

    async def draft_question(state: State, draft: RequestDraft, field: RequestField, kind: str) -> ClarifyingQuestion:
        out = await question_chain.ainvoke(_question_input(state, draft, field, kind))
        # The supported countries come from code, not the model, so the list is never wrong.
        options = sorted(ADZUNA_CURRENCY) if kind == "unsupported_country" else out.options
        return ClarifyingQuestion(about=field, text=out.text, options=options, answer=None)

    async def clarity_check(state: State) -> dict:
        draft = state.request_draft
        flags = _flag_missing(draft)
        profiled = _from_profile(state, draft, {a.about for a in _from_resume(state, draft, [])})
        # Fields the profile filled are settled, so no Clarifying Question repeats them.
        judged = await judge(state, draft, set(flags) | {a.about for a in profiled})
        for field, j in judged.items():
            if j.outcome:
                flags[field] = "ambiguous"

        # A field is asked until it has been asked MAX_ASKS times.
        to_ask = {f: k for f, k in flags.items() if sum(q.about == f for q in state.questions) < MAX_ASKS}

        # Each field's outcome and reason go to the run log, for `scout show`.
        outcomes = {}
        for field, j in judged.items():
            if field not in flags:
                outcomes[field.value] = {"outcome": "clear", "reason": j.reason or f"p_yes {j.p_yes:.2f} below cut {j.cut}"}
        for field, kind in flags.items():
            reason = f"{kind}: {judged[field].reason}" if field in judged and judged[field].reason else kind
            # A capped field only settles when nothing else is being asked; otherwise it is re-judged next pass.
            outcome = "ask" if field in to_ask else "at cap" if to_ask else "settle"
            outcomes[field.value] = {"outcome": outcome, "reason": reason}
        caveats = _caveats(judged)

        if to_ask:
            new = await asyncio.gather(*(draft_question(state, draft, f, k) for f, k in to_ask.items()))
            route = log_entry("clarity_check", LogKind.route, "asking " + ", ".join(f.value for f in to_ask), fields=outcomes)
            return {"questions": [*state.questions, *new], "run_log": [*state.run_log, *caveats, route]}

        # Nothing left to ask, so every flagged field is at the cap.
        request, assumptions, abort = _finish(draft, flags, deps.settings.default_country)
        if abort:
            route = log_entry("clarity_check", LogKind.route, f"aborted: {abort}", fields=outcomes)
            return {"run_log": [*state.run_log, *caveats, route]}
        route = log_entry("clarity_check", LogKind.route, "request is final", fields=outcomes)
        assumptions += _from_resume(state, draft, assumptions)
        assumptions += [a for a in profiled if a.about not in {x.about for x in assumptions}]
        return {"hiring_request": request, "assumptions": assumptions, "run_log": [*state.run_log, *caveats, route]}

    async def clarify(state: State) -> dict:
        pending = [q for q in state.questions if q.answer is None]
        answer = interrupt(ClarifyPause(payload=ClarifyPayload(questions=pending)))
        # Matched by position: the Controller can't check the count, so short answers pad blank and extras drop.
        filled = iter(answer.answers)
        questions = [
            q if q.answer is not None else q.model_copy(update={"answer": next(filled, "")})
            for q in state.questions
        ]
        return {"questions": questions, **log(state, "clarify", LogKind.pause, f"answered {len(pending)} questions")}

    async def plan(state: State) -> dict:
        search_plan = await plan_chain.ainvoke(_plan_input(state))
        message = f"plan: {', '.join(search_plan.titles)}, target {search_plan.target_postings}"
        return {"search_plan": search_plan, **log(state, "plan", LogKind.note, message)}

    async def plan_review(state: State) -> dict:
        # The Assumptions are shown here because this is the last chance to correct one before quota is spent.
        payload = PlanReviewPayload(
            plan=state.search_plan, assumptions=state.assumptions, calls_left=deps.gateway.calls_left(Source.adzuna),
            from_profile=profile_fields(state),
        )
        answer = interrupt(PlanReviewPause(payload=payload))
        # feedback is written even when null, so an approve after a reject clears the old feedback.
        update = {"plan_decision": answer.action, "plan_feedback": answer.feedback}
        if answer.action == PlanAction.edit:
            update["search_plan"] = answer.plan
        return {**update, **log(state, "plan_review", LogKind.pause, f"plan {answer.action}")}

    return {
        "intake": intake,
        "clarity_check": clarity_check,
        "clarify": clarify,
        "plan": plan,
        "plan_review": plan_review,
    }


def after_clarity(state: State) -> str:
    if any(q.answer is None for q in state.questions):
        return "clarify"
    return "plan" if state.hiring_request else END


def after_review(state: State) -> str:
    if state.plan_decision == PlanAction.abort:
        return END
    return "plan" if state.plan_decision == PlanAction.reject else "fetch_agent"


ROUTERS: dict[str, Router] = {"clarity_check": after_clarity, "plan_review": after_review}
