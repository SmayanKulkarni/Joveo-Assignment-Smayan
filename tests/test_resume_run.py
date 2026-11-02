import asyncio
import pathlib
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from talent_scout.analysis.types import ResumeFacts, ResumeSkill, Role
from talent_scout.brief.nodes import _resume_note
from talent_scout.clients import web
from talent_scout.kernel.state import State
from talent_scout.kernel.testing import fake_classifier, make_settings
from talent_scout.kernel.types import RequestField
from talent_scout.request_plan.nodes import _intake_input, make_nodes
from test_accounts_api import customer_of, wait_idle
from test_brief_writer import REQUEST, Scripted, reply, stats, write
from test_request_plan import draft, make_deps, run
from test_resume import RESUME, Chain, extraction

UPLOADED = date(2026, 11, 2)


def facts(*skills, title="Staff Data Engineer", seniority="lead", places=("Berlin",)) -> ResumeFacts:
    return ResumeFacts(
        roles=[Role(title="Intern", start="2012", end="2013"), Role(title=title, start="2018", end="Present")],
        skills=[ResumeSkill(name=s, added=s.startswith("+")) for s in skills],
        seniority=seniority, locations=list(places), years=8,
    )


def state(**over) -> State:
    return State(**{"request_text": "Data Engineer", "resume": facts("Python"), "resume_uploaded": UPLOADED, **over})


def test_the_latest_role_is_the_one_that_ends_last_whatever_the_order():
    assert facts().latest_title == "Staff Data Engineer"
    assert ResumeFacts(roles=[], skills=[], seniority="unknown", locations=[], years=None).latest_title is None


def test_the_intake_prompt_gains_the_facts_only_when_there_is_a_resume():
    plain = _intake_input(State(request_text="Data Engineer"))
    assert "Resume" not in plain
    prompt = _intake_input(state())
    assert plain in prompt and "role: Staff Data Engineer" in prompt and "seniority: lead" in prompt and "location: Berlin" in prompt
    # An unknown seniority and an empty place offer nothing.
    bare = state(resume=facts(seniority="unknown", places=()))
    assert "seniority" not in _intake_input(bare) and "location" not in _intake_input(bare)


def clarity(st: State, **fields):
    deps = make_deps(classifier=fake_classifier({"role": 0.1, "location": 0.1, "seniority": 0.1}))[0]
    return run(make_nodes(deps)["clarity_check"], st.model_copy(update={"request_draft": draft(**fields)}))


def test_each_field_taken_from_the_resume_is_an_assumption_and_typed_words_win():
    update = clarity(state(request_text="Data Analyst, Bangalore"), role="Data Analyst", location="Bangalore", seniority="lead")
    # The role and place were typed, so only seniority is the Resume's.
    assert [(a.about, a.value) for a in update["assumptions"]] == [(RequestField.seniority, "lead")]
    assert update["assumptions"][0].reason == "from the Resume uploaded 2026-11-02"

    sparse = clarity(state(request_text="data work"), role="Staff Data Engineer", location="Berlin", country="de", seniority="lead")
    assert [a.about for a in sparse["assumptions"]] == [RequestField.role, RequestField.seniority, RequestField.location]

    no_resume = clarity(State(request_text="Data Analyst, Bangalore"), role="Data Analyst")
    assert no_resume["assumptions"] == []


def test_a_clarifying_question_is_still_asked_when_the_resume_cannot_settle_it():
    deps = make_deps(
        cheap=['{"text": "Which role?", "options": []}'], classifier=fake_classifier({"role": 0.9, "location": 0.1}),
    )[0]
    update = run(make_nodes(deps)["clarity_check"], state().model_copy(update={"request_draft": draft(role="Engineer")}))
    assert [q.about for q in update["questions"]] == [RequestField.role] and "assumptions" not in update


def test_the_run_notes_line_names_the_upload_date_and_the_csm_added_facts():
    assert _resume_note(State(request_text="x")) is None
    plain = _resume_note(state())
    assert plain == "Resume uploaded on 2026-11-02"
    added = _resume_note(state().model_copy(update={"resume": facts("Python", "+Terraform")}))
    assert added == "Resume uploaded on 2026-11-02; facts added by the CSM: +Terraform"


def test_write_brief_never_receives_the_resume():
    secret = facts("Zymurgy", title="Quokka Wrangler", places=("Atlantis",))
    model = Scripted(messages=iter([]), script=[reply()])
    write(model, resume=secret, resume_uploaded=UPLOADED)
    sent = " ".join(str(m.content) for m in model.seen[0])
    assert not any(word in sent for word in ("Zymurgy", "Quokka", "Atlantis", "Resume"))


# a Run starts with the Resume as it stands, and only its Customer's


@pytest.fixture
def client(tmp_path):
    settings = make_settings(demo=True, demo_delay=0.02, runs_db=tmp_path / "runs.sqlite", runs_dir=tmp_path / "runs")
    with TestClient(web.make_app(settings), base_url="http://127.0.0.1") as c:
        c.app.state.resume_chain = Chain()
        yield c


def stored_input(client, thread_id) -> State:
    return client.portal.call(client.app.state.controller.get_run, thread_id).state


def test_a_run_copies_its_customers_resume_and_a_later_upload_leaves_it_alone(client):
    first, second = customer_of(client, "First"), customer_of(client, "Second")
    client.put(f"/api/customers/{first}/resume", content=RESUME.encode())
    client.app.state.resume_chain = Chain(extraction(skills=["Kafka"], roles=[], locations=[]))
    client.put(f"/api/customers/{second}/resume", content=RESUME.encode())

    def start(customer):
        thread_id = client.post("/api/runs", json={"request_text": "Data Engineer", "customer_id": customer}).json()["thread_id"]
        wait_idle(client, thread_id)
        return stored_input(client, thread_id)

    one, other = start(first), start(second)
    assert [s.name for s in one.resume.skills][0] == "Python" and one.resume_uploaded == date.today()
    assert [s.name for s in other.resume.skills] == ["Kafka"]

    # Re-uploading changes the next Run and not the one already made.
    thread_id = client.get(f"/api/runs?customer_id={first}").json()[0]["thread_id"]
    client.put(f"/api/customers/{first}/resume", content=RESUME.encode())
    assert [s.name for s in stored_input(client, thread_id).resume.skills][0] == "Python"
    # A Customer with no Resume starts a Run with none.
    bare = start(customer_of(client, "Bare"))
    assert bare.resume is None and bare.resume_uploaded is None


def test_a_runs_prompts_hold_nothing_of_another_customers_resume():
    mine = facts("Python", title="Quokka Wrangler", places=("Atlantis",))
    deps, cheap, strong, _ = make_deps(
        cheap=[draft(role="Quokka Wrangler").model_dump_json()], classifier=fake_classifier({"role": 0.1, "location": 0.1}),
    )
    other = State(request_text="Data Engineer", resume=mine, resume_uploaded=UPLOADED)
    nodes = make_nodes(deps)
    run(nodes["intake"], State(request_text="Data Engineer", resume=facts("Rust", title="Zebra Tamer", places=("Oslo",))))
    sent = " ".join(str(m.content) for call in cheap.seen for m in call)
    assert "Zebra" in sent and "Quokka" not in sent and "Atlantis" not in sent
    assert other.resume.latest_title == "Quokka Wrangler"


def test_no_node_package_can_reach_the_database_or_the_accounts():
    root = pathlib.Path(web.__file__).parents[1]
    for package in ("request_plan", "collection", "analysis", "brief", "kernel"):
        for path in (root / package).glob("*.py"):
            if path.name == "resume.py":
                continue  # parses an upload; it is called by the API layer, not by a node
            source = path.read_text(encoding="utf-8")
            assert not re.search(r"runtime\.accounts|runtime\.registry|aiosqlite|psycopg", source), path.name
