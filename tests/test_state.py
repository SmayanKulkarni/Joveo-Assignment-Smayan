import logging
import sqlite3

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import ValidationError

from talent_scout.analysis.types import Extraction
from talent_scout.kernel.state import LogKind, RunLogEntry, State, StateWriteError, log, owned
from talent_scout.kernel.types import Model, SearchPlan


class Item(Model):
    key: str


def run(fn, state, owner="collection"):
    return owned("node", owner)(fn)(state)


def test_log_appends_and_caveat_kind_exists():
    s = State(request_text="r")
    first = log(s, "n", LogKind.caveat, "m", dimension="demand", posting_keys=["a:1"])
    s2 = State(request_text="r", **first)
    assert [e.message for e in log(s2, "n", LogKind.note, "m2")["run_log"]] == ["m", "m2"]


def test_run_log_data_is_plain_json_only():
    with pytest.raises(ValidationError):
        RunLogEntry(node="n", kind=LogKind.note, message="m", data={"x": object()})
    with pytest.raises(ValidationError):  # no timestamp field
        RunLogEntry(node="n", kind=LogKind.note, message="m", data={}, at="now")


def test_current_plan_prefers_latest_broadened_plan():
    base = SearchPlan(titles=["a"], country="us", locations=["x"], radius_km=0, max_days_old=1, target_postings=20, category=None)
    wider = base.model_copy(update={"radius_km": 50})
    assert State(request_text="r").current_plan is None
    assert State(request_text="r", search_plan=base).current_plan == base
    assert State(request_text="r", search_plan=base, broadened_plans=[wider]).current_plan == wider


def test_guard_rejects_wrong_owner():
    with pytest.raises(StateWriteError, match="belongs to 'analysis'"):
        run(lambda s: {"stats": None}, State(request_text="r"))


def test_guard_rejects_bad_value_type_and_chains_validation_error():
    with pytest.raises(StateWriteError) as e:
        run(lambda s: {"sample": "not-a-list"}, State(request_text="r"))
    assert isinstance(e.value.__cause__, ValidationError)


def test_guard_rejects_wiped_run_log():
    s = State(request_text="r", **log(State(request_text="r"), "n", LogKind.note, "m"))
    with pytest.raises(StateWriteError, match="current log"):
        run(lambda s: {"run_log": []}, s)


def test_guard_rejects_send_with_non_model_arg():
    with pytest.raises(StateWriteError, match="Send arg"):
        run(lambda s: [Send("extract", {"key": "a"})], State(request_text="r"))


def test_run_log_open_to_every_owner_but_input_fields_to_none():
    s = State(request_text="r")
    for owner in ("collection", "analysis", "brief"):
        assert run(lambda s: log(s, "n", LogKind.note, "m"), s, owner)
    for key in ("request_text", "focus"):
        with pytest.raises(StateWriteError):
            run(lambda s: {key: getattr(s, key)}, s, "collection")


def test_state_is_frozen():
    with pytest.raises(ValidationError):
        State(request_text="r").sample = ["x"]


def build_graph(checkpointer):
    def start(state: State):
        return log(state, "start", LogKind.note, "begin")

    def fan(state: State):
        return [Send("extract", Item(key=f"adzuna:{i}")) for i in range(3)]

    def extract(item: Item):
        return {"extractions": {item.key: Extraction(skills=[], seniority="unknown", years_min=None, employer_type="unknown", ungrounded=0)}}

    g = StateGraph(State)
    g.add_node("start", owned("start", "request_plan")(start))
    g.add_node("extract", owned("extract", "analysis")(extract))
    g.add_edge(START, "start")
    g.add_conditional_edges("start", owned("fan", "analysis")(fan), ["extract"])
    g.add_edge("extract", END)
    return g.compile(checkpointer=checkpointer)


def test_send_fan_out_merges_and_round_trips_through_sqlite_checkpoint(tmp_path, caplog):
    from langgraph.checkpoint.serde import _msgpack
    from langgraph.checkpoint.serde import jsonplus

    assert _msgpack.STRICT_MSGPACK_ENABLED
    jsonplus._warned_unregistered_types.clear()  # the warning is deduped per process
    caplog.set_level(logging.WARNING)
    conn = sqlite3.connect(tmp_path / "cp.sqlite", check_same_thread=False)
    graph = build_graph(SqliteSaver(conn))
    config = {"configurable": {"thread_id": "t"}}

    graph.invoke({"request_text": "r"}, config)

    # A fresh graph on the same file proves state is rehydrated from the checkpoint.
    restored = State.model_validate(build_graph(SqliteSaver(conn)).get_state(config).values)
    assert sorted(restored.extractions) == ["adzuna:0", "adzuna:1", "adzuna:2"]
    assert restored.run_log[0].message == "begin"
    assert "unregistered" not in caplog.text


def test_guard_rejects_returned_model_and_command_update():
    from langgraph.types import Command

    with pytest.raises(StateWriteError):
        run(lambda s: s, State(request_text="r"))
    with pytest.raises(StateWriteError):
        run(lambda s: Command(update={"stats": None}), State(request_text="r"))


def test_owned_rejects_unknown_owner():
    with pytest.raises(ValueError):
        owned("n", "colection")
