import asyncio
import json

import aiosqlite
import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_typesafe import NoulAnswer
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from pydantic import Field, ValidationError

from talent_scout.gateway.testing import FakeGateway
from talent_scout.kernel.jev import Jev, _FallbackResponse
from talent_scout.kernel.llm import Tiers
from talent_scout.kernel.state import LogKind, State
from talent_scout.kernel.testing import FakeClassifier, FakeToolChatModel, fake_classifier, make_settings
from talent_scout.kernel.thresholds import CUTS
from talent_scout.kernel.types import ADZUNA_CURRENCY, Assumption, ClarifyingQuestion, Dimension, RequestField, SearchPlan
from talent_scout.request_plan.nodes import ROUTERS, after_clarity, after_review, make_nodes
from talent_scout.request_plan.types import ClarifyAnswer, PlanAction, RequestDraft
from talent_scout.runtime.deps import Deps
from talent_scout.runtime.graph import build_graph
from talent_scout.runtime.pause import ALLOWED_MSGPACK, ANSWERS
from talent_scout.runtime.testing import ANSWER_FOR


class Scripted(FakeToolChatModel):
    """Replays JSON replies in order and keeps every prompt it was sent."""

    script: list = Field(default_factory=list)
    seen: list = Field(default_factory=list)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.script.pop(0)))])


class Sequenced(FakeClassifier):
    """A classifier whose answers change from one request to the next."""

    def __init__(self, *rounds):
        super().__init__({}, "typesafe/jev-1.14-20260101", [])
        self.rounds = list(rounds)

    def invoke(self, input, config=None, **kwargs):
        self.answers = self.rounds.pop(0)
        return super().invoke(input, config)


class Fallback(FakeClassifier):
    def invoke(self, input, config=None, **kwargs):
        self.calls.append(input)
        return _FallbackResponse(
            model="llm:cheap",
            answers={q: NoulAnswer(type="noul", noul=0.0) for q in input["questions"]},
            reasons={q: "clear" for q in input["questions"]},
        )


def draft(**over) -> RequestDraft:
    base = dict(role="Data Analyst", location="Bangalore", country="in", seniority=None, employment_type=None,
                work_mode=None, currency=None, purpose=None)
    return RequestDraft(**{**base, **over})


def plan_json(**over) -> str:
    base = dict(titles=["Data Analyst"], country="in", locations=["Bangalore"], radius_km=25, max_days_old=30,
                target_postings=100, category=None)
    return SearchPlan(**{**base, **over}).model_dump_json()


def question(about=RequestField.role, answer=None) -> ClarifyingQuestion:
    return ClarifyingQuestion(about=about, text=f"Which {about.value}?", options=[], answer=answer)


def question_json(text="Which one?", options=()) -> str:
    return json.dumps({"text": text, "options": list(options)})


def make_deps(cheap=(), strong=(), classifier=None, **settings):
    cheap_model, strong_model = Scripted(messages=iter([]), script=list(cheap)), Scripted(messages=iter([]), script=list(strong))
    settings = make_settings(**settings)
    classifier = classifier or fake_classifier({})
    deps = Deps(Tiers({"cheap": [cheap_model], "strong": [strong_model]}, settings), Jev(classifier, CUTS), FakeGateway([]), settings)
    return deps, cheap_model, strong_model, classifier


def run(node, state: State) -> dict:
    return asyncio.run(node(state))


def state_with(**over) -> State:
    return State(request_text=over.pop("request_text", "Data Analyst, Bangalore"), **over)


def final_request():
    return run(
        make_nodes(make_deps(classifier=fake_classifier({"role": 0.1, "location": 0.1}))[0])["clarity_check"],
        state_with(request_draft=draft()),
    )["hiring_request"]


def route(update: dict):
    return next(e for e in reversed(update["run_log"]) if e.kind == LogKind.route)


def test_intake_writes_the_draft_and_the_answers_reach_the_prompt():
    deps, cheap, _, _ = make_deps(cheap=[draft(role="Software Engineer").model_dump_json()])
    state = state_with(
        request_text="Engineer, Texas",
        questions=[question(answer="Software"), question(RequestField.location, answer="  ")],
    )

    update = run(make_nodes(deps)["intake"], state)

    assert update["request_draft"].role == "Software Engineer"
    assert [e.kind for e in update["run_log"]] == [LogKind.note]
    prompt = cheap.seen[0][-1].content
    assert "Engineer, Texas" in prompt and "Software" in prompt
    assert "Which location?" not in prompt  # a blank answer says nothing


def test_clear_request_gets_no_question_and_sets_hiring_request():
    deps, cheap, _, jev = make_deps(classifier=fake_classifier({"role": 0.1, "location": 0.1}))

    update = run(make_nodes(deps)["clarity_check"], state_with(request_draft=draft()))

    assert update["hiring_request"].country == "in" and update["assumptions"] == []
    assert "questions" not in update and cheap.seen == []
    assert set(jev.calls[0]["questions"]) == {"role", "location"}  # no seniority was given
    assert set(route(update).data["fields"]) == {"role", "location"}


def test_seniority_is_judged_only_when_the_user_gave_one():
    deps, _, _, jev = make_deps(classifier=fake_classifier({"role": 0.1, "location": 0.1, "seniority": 0.1}))

    run(make_nodes(deps)["clarity_check"], state_with(request_draft=draft(seniority="Senior")))

    assert set(jev.calls[0]["questions"]) == {"role", "location", "seniority"}


def test_missing_fields_skip_jev_and_only_flagged_fields_are_asked():
    deps, cheap, _, jev = make_deps(cheap=[question_json("Where?")], classifier=fake_classifier({"role": 0.1}))

    update = run(make_nodes(deps)["clarity_check"], state_with(request_draft=draft(location=None, country=None)))

    assert set(jev.calls[0]["questions"]) == {"role"}  # location was flagged by code, so Jev isn't asked
    assert [(q.about, q.answer) for q in update["questions"]] == [(RequestField.location, None)]
    assert "hiring_request" not in update and "assumptions" not in update  # nothing settles while a question is out


def test_no_jev_call_when_every_field_is_flagged_by_code():
    deps, _, _, jev = make_deps(cheap=[question_json("What role?"), question_json("Where?")])

    update = run(make_nodes(deps)["clarity_check"], state_with(request_draft=draft(role=None, location=None, country=None)))

    assert jev.calls == []
    assert {q.about for q in update["questions"]} == {RequestField.role, RequestField.location}


def test_an_ambiguous_field_is_asked_with_the_earlier_wording_in_the_prompt():
    deps, cheap, _, _ = make_deps(
        cheap=[question_json("Which kind?", ["Software", "Civil", "Mechanical", "Electrical"])],
        classifier=fake_classifier({"role": 0.9, "location": 0.1}),
    )
    earlier = question(answer="Engineer")

    update = run(make_nodes(deps)["clarity_check"], state_with(request_draft=draft(role="Engineer"), questions=[earlier]))

    assert [q.about for q in update["questions"][1:]] == [RequestField.role]
    assert earlier.text in cheap.seen[0][-1].content


def test_a_question_about_an_unsupported_country_lists_the_supported_ones():
    deps, _, _, _ = make_deps(cheap=[question_json("Which country?", ["Japan"])], classifier=fake_classifier({"role": 0.1}))

    update = run(make_nodes(deps)["clarity_check"], state_with(request_draft=draft(location="Tokyo", country="jp")))

    assert update["questions"][0].options == sorted(ADZUNA_CURRENCY)


def test_a_third_ask_settles_a_vague_field_with_an_assumption_and_no_llm_call():
    deps, cheap, _, _ = make_deps(classifier=fake_classifier({"role": 0.9, "location": 0.1}))
    asked = [question(answer="Engineer"), question(answer="Engineer")]

    update = run(make_nodes(deps)["clarity_check"], state_with(request_draft=draft(role="Engineer"), questions=asked))

    assert update["hiring_request"].role == "Engineer"
    assert [(a.about, a.value) for a in update["assumptions"]] == [(RequestField.role, "Engineer")]
    assert cheap.seen == [] and "questions" not in update


SETTLED = [question(RequestField.location, answer=""), question(RequestField.location, answer="")]


def test_a_null_location_settles_on_the_default_country():
    deps, _, _, _ = make_deps(classifier=fake_classifier({"role": 0.1}), default_country="gb")

    update = run(make_nodes(deps)["clarity_check"], state_with(request_draft=draft(location=None, country=None), questions=SETTLED))

    request = update["hiring_request"]
    assert (request.location, request.country) == ("gb", "gb")
    assert [a.about for a in update["assumptions"]] == [RequestField.location]


@pytest.mark.parametrize(
    "bad, asked",
    [
        (dict(location="Tokyo", country="jp"), SETTLED),
        (dict(role=None), [question(answer=""), question(answer="")]),
    ],
    ids=["unsupported-country", "null-role"],
)
def test_an_unusable_field_at_the_cap_aborts_the_run(bad, asked):
    deps, _, _, _ = make_deps(classifier=fake_classifier({"role": 0.1, "location": 0.1}))

    update = run(make_nodes(deps)["clarity_check"], state_with(request_draft=draft(**bad), questions=asked))

    assert "hiring_request" not in update and "assumptions" not in update
    assert route(update).message.startswith("aborted: ")


def test_a_fallback_judgement_logs_a_caveat():
    deps, _, _, _ = make_deps(classifier=Fallback({}, "", []))

    update = run(make_nodes(deps)["clarity_check"], state_with(request_draft=draft()))

    assert [e.kind for e in update["run_log"]] == [LogKind.caveat, LogKind.route]
    assert "hiring_request" in update


def test_after_clarity_outcomes():
    request = final_request()
    assert after_clarity(state_with(questions=[question()])) == "clarify"
    assert after_clarity(state_with(questions=[question(answer="x")], hiring_request=request)) == "plan"
    assert after_clarity(state_with(questions=[question(answer="x")])) == END
    assert ROUTERS["clarity_check"] is after_clarity


def one_node_graph(deps):
    builder = StateGraph(State)
    builder.add_node("clarify", make_nodes(deps)["clarify"])
    builder.add_edge(START, "clarify")
    builder.add_edge("clarify", END)
    saver = InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=ALLOWED_MSGPACK))
    return builder.compile(checkpointer=saver)


@pytest.mark.parametrize(
    "answers, expected",
    [(["a", "b"], ["x", "a", "b"]), (["a"], ["x", "a", ""]), (["a", "b", "c", "d"], ["x", "a", "b"])],
    ids=["exact", "padded", "extras-dropped"],
)
def test_clarify_pauses_with_the_unanswered_and_matches_answers_by_position(answers, expected):
    async def go():
        graph = one_node_graph(make_deps()[0])
        config = {"configurable": {"thread_id": "t"}}
        start = {"request_text": "x", "questions": [question(answer="x"), question(), question(RequestField.location)]}
        await graph.ainvoke(start, config)
        pause = (await graph.aget_state(config)).interrupts[0].value
        await graph.ainvoke(Command(resume=ANSWERS["clarify"].model_validate({"answers": answers})), config)
        return pause, (await graph.aget_state(config)).values["questions"]

    pause, questions = asyncio.run(go())

    assert [q.about for q in pause.payload.questions] == [RequestField.role, RequestField.location]
    assert [q.answer for q in questions] == expected


def test_plan_retries_a_bad_plan_with_feedback_and_ignores_focus():
    too_many_titles = json.dumps({**json.loads(plan_json()), "radius_km": 500})
    deps, _, strong, _ = make_deps(strong=[too_many_titles, plan_json()])
    state = state_with(hiring_request=final_request(), focus=[Dimension.compensation])

    update = run(make_nodes(deps)["plan"], state)

    assert update["search_plan"].titles == ["Data Analyst"]
    assert "That failed validation" in strong.seen[1][-1].content
    assert "compensation" not in strong.seen[0][-1].content
    assert update["run_log"][-1].kind == LogKind.note


def test_plan_after_a_reject_sees_the_previous_plan_and_feedback():
    deps, _, strong, _ = make_deps(strong=[plan_json()])
    previous = SearchPlan.model_validate_json(plan_json(titles=["Old Title"]))
    state = state_with(hiring_request=final_request(), search_plan=previous, plan_decision=PlanAction.reject, plan_feedback="Wider radius")

    run(make_nodes(deps)["plan"], state)

    prompt = strong.seen[0][-1].content
    assert "Old Title" in prompt and "Wider radius" in prompt


def review(answers, **settings):
    """Runs plan_review, the real plan node and after_review in a loop, answering each Pause from `answers`."""
    deps, _, strong, _ = make_deps(strong=[plan_json(titles=["Second Title"])] * 2, **settings)
    nodes = make_nodes(deps)
    builder = StateGraph(State)
    builder.add_node("plan_review", nodes["plan_review"])
    builder.add_node("plan", nodes["plan"])
    builder.add_conditional_edges(START, lambda s: "plan_review", ["plan_review"])
    builder.add_conditional_edges("plan_review", after_review, ["plan", "fetch_agent", END])
    builder.add_node("fetch_agent", lambda s: {})
    builder.add_edge("plan", "plan_review")
    builder.add_edge("fetch_agent", END)
    saver = InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=ALLOWED_MSGPACK))
    graph = builder.compile(checkpointer=saver)
    request = final_request()

    async def go():
        config = {"configurable": {"thread_id": "t"}}
        start = {
            "request_text": "x", "hiring_request": request, "search_plan": SearchPlan.model_validate_json(plan_json()),
            "assumptions": [Assumption(about=RequestField.role, value="Engineer", reason="vague")],
        }
        await graph.ainvoke(start, config)
        pauses = []
        for answer in answers:
            pauses.append((await graph.aget_state(config)).interrupts[0].value)
            await graph.ainvoke(Command(resume=ANSWERS["plan_review"].model_validate(answer)), config)
        return pauses, State.model_validate((await graph.aget_state(config)).values)

    pauses, state = asyncio.run(go())
    return pauses, state, strong


def action(name, plan=None, feedback=None):
    return {"action": name, "plan": plan and json.loads(plan), "feedback": feedback}


def test_plan_review_pauses_with_the_plan_and_assumptions_and_an_approve_keeps_the_plan():
    pauses, state, _ = review([action("approve")])

    assert pauses[0].payload.plan.titles == ["Data Analyst"]
    assert [a.about for a in pauses[0].payload.assumptions] == [RequestField.role]
    assert state.plan_decision == PlanAction.approve and state.search_plan.titles == ["Data Analyst"]
    assert [e.kind for e in state.run_log] == [LogKind.pause]


def test_an_edit_replaces_the_search_plan():
    _, state, _ = review([action("edit", plan_json(titles=["Edited Title"], radius_km=50))])

    assert (state.search_plan.titles, state.search_plan.radius_km) == (["Edited Title"], 50)


def test_a_reject_sends_its_feedback_to_the_next_plan_and_rejects_have_no_cap():
    pauses, state, strong = review([action("reject", feedback="Wider radius"), action("reject", feedback="Again")])

    assert "Wider radius" in strong.seen[0][-1].content
    assert len(pauses) == 2 and state.plan_decision == PlanAction.reject


def test_an_abort_ends_the_run():
    _, state, _ = review([action("abort")])

    assert state.plan_decision == PlanAction.abort


def test_a_bad_edit_is_refused_before_it_reaches_the_node():
    bad = json.loads(plan_json()) | {"radius_km": 500}

    with pytest.raises(ValidationError):
        ANSWERS["plan_review"].model_validate({"action": "edit", "plan": bad, "feedback": None})


def test_after_review_outcomes():
    assert after_review(state_with(plan_decision=PlanAction.abort)) == END
    assert after_review(state_with(plan_decision=PlanAction.reject)) == "plan"
    assert after_review(state_with(plan_decision=PlanAction.approve)) == "fetch_agent"
    assert after_review(state_with(plan_decision=PlanAction.edit)) == "fetch_agent"
    assert after_review(state_with()) == "fetch_agent"


def drive(deps, request_text, tmp_path):
    """Runs the real Request & Plan, answering every Pause and stopping before fetch_agent."""

    async def go():
        async with aiosqlite.connect(tmp_path / "runs.sqlite") as conn:
            saver = AsyncSqliteSaver(conn, serde=JsonPlusSerializer(allowed_msgpack_modules=ALLOWED_MSGPACK))
            await saver.setup()
            graph = build_graph(deps, saver)
            config = {"configurable": {"thread_id": "t1"}}
            command, kinds = {"request_text": request_text}, []
            while True:
                await graph.ainvoke(command, config, interrupt_before=["fetch_agent"])
                snapshot = await graph.aget_state(config)
                if not snapshot.interrupts:
                    return kinds, State.model_validate(snapshot.values)
                pause = snapshot.interrupts[0].value
                kinds.append(pause.kind)
                answer = {"answers": ["Software"]} if pause.kind == "clarify" else ANSWER_FOR[pause.kind]
                command = Command(resume=ANSWERS[pause.kind].model_validate(answer))

    return asyncio.run(go())


def test_a_clear_request_reaches_fetch_agent_with_a_plan(tmp_path):
    deps, *_ = make_deps(
        cheap=[draft().model_dump_json()], strong=[plan_json()],
        classifier=fake_classifier({"role": 0.1, "location": 0.1}),
    )

    kinds, state = drive(deps, "Data Analyst, Bangalore", tmp_path)

    assert "clarify" not in kinds
    assert [e.node for e in state.run_log] == ["intake", "clarity_check", "plan", "plan_review"]
    assert state.search_plan.titles == ["Data Analyst"]


def test_texas_goes_through_a_real_clarify_loop_to_fetch_agent(tmp_path):
    texas = draft(role="Engineer", location="Texas", country="us")
    answered = draft(role="Software Engineer", location="Texas", country="us")
    deps, *_ = make_deps(
        cheap=[texas.model_dump_json(), question_json("Which engineer?", ["Software"]), answered.model_dump_json()],
        strong=[plan_json(titles=["Software Engineer"], country="us", locations=["Texas"])],
        classifier=Sequenced({"role": 0.9, "location": 0.1}, {"role": 0.1, "location": 0.1}),
    )

    kinds, state = drive(deps, "Engineer, Texas", tmp_path)

    nodes = [e.node for e in state.run_log]
    assert kinds[0] == "clarify"
    assert nodes == ["intake", "clarity_check", "clarify", "intake", "clarity_check", "plan", "plan_review"]
    assert state.hiring_request.role == "Software Engineer"
    assert state.search_plan.titles == ["Software Engineer"]
