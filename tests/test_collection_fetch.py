import asyncio

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from talent_scout.collection.nodes import MAX_FETCHES, after_fetch_agent, make_nodes
from talent_scout.collection.testing import ai_calls, make_deps, plan, posting, record, result, search_call, state_with
from talent_scout.gateway.types import SourceRejected, SourceUnavailable
from talent_scout.kernel.state import LogKind, State
from talent_scout.kernel.types import Source


def run(node, state: State) -> dict:
    return asyncio.run(node(state))


def asked(*calls, **state_over) -> State:
    """A state whose last message is the model's tool calls, as `tools` receives it."""
    return state_with(messages=[SystemMessage("s"), HumanMessage("h"), ai_calls(*calls)], **state_over)


def fetch_agent_turn(script, **state_over):
    deps, cheap, _, _ = make_deps(cheap=script)
    update = run(make_nodes(deps)["fetch_agent"], state_with(**state_over))
    return update, cheap


def test_bound_schemas_hide_plan_and_attempt_and_a_non_us_plan_binds_only_adzuna():
    _, cheap = fetch_agent_turn([ai_calls()], search_plan=plan(country="us"))
    schemas = {t.name: convert_to_openai_tool(t)["function"]["parameters"]["properties"] for t in cheap.bound_tools}

    assert set(schemas) == {"search_adzuna", "search_usajobs"}
    assert all(set(props) == {"title", "page"} for props in schemas.values())

    _, cheap = fetch_agent_turn([ai_calls()])
    assert [t.name for t in cheap.bound_tools] == ["search_adzuna"]


def test_model_args_cannot_override_the_plan_or_attempt():
    deps, *_, gateway = make_deps(results=[result([posting("1")])])
    call = search_call("Data Analyst")
    call["args"] |= {"plan": plan(country="gb", location="London").model_dump(), "attempt": 9}

    update = run(make_nodes(deps)["tools"], asked(call))

    (rec,) = update["fetches"]
    assert (rec.attempt, gateway.fetches[0].country, gateway.fetches[0].location) == (0, "in", "bangalore")


def test_each_tool_passes_its_own_source_and_the_plan_builds_the_fetch():
    deps, *_, gateway = make_deps(results=[result([], source=Source.adzuna), result([], source=Source.usajobs)])
    state = asked(
        search_call("Data Analyst", id="a"), search_call("Analyst", tool="search_usajobs", page=2, id="u"),
        search_plan=plan(country="us", location="Texas", radius_km=10, category="it-jobs"),
    )

    update = run(make_nodes(deps)["tools"], state)

    assert gateway.sources == [Source.adzuna, Source.usajobs]
    fetch = gateway.fetches[1]
    assert (fetch.title, fetch.page, fetch.country, fetch.location, fetch.radius_km, fetch.max_days_old, fetch.category) == (
        "analyst", 2, "us", "texas", 10, 30, "it-jobs",
    )
    assert [r.source for r in update["fetches"]] == [Source.adzuna, Source.usajobs]


def test_usajobs_is_an_unknown_tool_on_a_non_us_plan():
    deps, *_, gateway = make_deps()

    update = run(make_nodes(deps)["tools"], asked(search_call("Analyst", tool="search_usajobs")))

    (message,) = update["messages"][-1:]
    assert message.status == "error" and "Unknown tool" in message.content
    assert update["fetches"] == [] and gateway.fetches == []


def test_a_failed_source_leaves_a_record_with_the_error_and_a_message_with_its_text():
    deps, *_ = make_deps(results=[SourceUnavailable("adzuna is down")])

    update = run(make_nodes(deps)["tools"], asked(search_call("Data Analyst")))

    (rec,) = update["fetches"]
    assert rec.result is None and rec.error == "adzuna is down"
    assert "adzuna failed: adzuna is down." in update["messages"][-1].content


def test_bad_args_give_an_error_message_and_no_record():
    deps, *_ = make_deps()
    call = search_call("Data Analyst")
    call["args"]["page"] = "two"

    update = run(make_nodes(deps)["tools"], asked(call))

    assert update["messages"][-1].status == "error" and update["fetches"] == []


def test_a_blank_title_is_a_bad_fetch_not_a_failed_source():
    deps, *_ = make_deps()

    update = run(make_nodes(deps)["tools"], asked(search_call("  ")))

    assert update["messages"][-1].status == "error" and update["fetches"] == []


def test_a_call_over_the_cap_is_refused_and_every_message_counts():
    deps, *_, gateway = make_deps(results=[result([])] * MAX_FETCHES)
    done = [ToolMessage(content="x", tool_call_id=str(i)) for i in range(MAX_FETCHES - 1)]
    state = state_with(messages=[*done, ai_calls(search_call("a", id="1"), search_call("b", id="2"))])

    update = run(make_nodes(deps)["tools"], state)

    refused = update["messages"][-1]
    assert len(gateway.fetches) == 1 and refused.status == "error" and "Refused" in refused.content
    assert len(update["fetches"]) == 1


def test_failed_calls_read_plainly_on_the_card_and_unchanged_to_the_model(monkeypatch):
    cards = []
    monkeypatch.setattr("talent_scout.collection.nodes.emit", cards.append)
    deps, *_ = make_deps(results=[SourceUnavailable("Adzuna is down")])
    over = search_call("c", id="3")
    over["name"] = "search_nowhere"

    update = run(make_nodes(deps)["tools"], asked(search_call("a", id="1"), over))

    assert [c["summary"] for c in cards if c["type"] == "tool_returned"] == ["Didn't run", "Didn't run"]
    assert "Unknown tool" in update["messages"][-1].content


def test_bad_args_and_refusals_use_up_the_cap_like_good_calls():
    deps, *_, gateway = make_deps(results=[result([])])
    bad = search_call("a", id="1")
    bad["args"]["page"] = "two"
    state = asked(bad, search_call("b", id="2"))

    first = run(make_nodes(deps)["tools"], state)
    # Two ToolMessages (one bad, one good) now sit in messages, so only MAX_FETCHES - 2 slots remain.
    left = MAX_FETCHES - sum(isinstance(m, ToolMessage) for m in first["messages"])
    assert left == MAX_FETCHES - 2 and len(gateway.fetches) == 1


def test_source_rejected_propagates():
    deps, *_ = make_deps(results=[SourceRejected(Source.adzuna, 401, "bad key")])

    with pytest.raises(SourceRejected):
        run(make_nodes(deps)["tools"], asked(search_call("Data Analyst")))


def test_the_summary_follows_the_format_and_carries_no_posting_text_beyond_titles():
    postings = [posting(str(i), title=f"Data Analyst {i}") for i in range(7)]
    deps, *_ = make_deps(results=[result(postings, total=3200, calls_left=17)])
    earlier = record([postings[0]])
    state = asked(search_call("Data Analyst"), fetches=[earlier])

    update = run(make_nodes(deps)["tools"], state)

    content = update["messages"][-1].content
    lines = content.splitlines()
    assert lines[0] == 'adzuna "data analyst" page 1: 7 Postings, 6 new.'
    assert lines[1] == "About 3,200 matches, 17 calls left."
    assert lines[2] == "Sample titles: " + "; ".join(f"Data Analyst {i}" for i in range(5)) + "."
    assert not any(p.description in content or p.url in content or p.company in content for p in postings)
    # fetches is written whole, so the earlier record survives beside the new one
    assert [r.fetch.title for r in update["fetches"]] == ["data analyst", "data analyst"] and update["fetches"][0] == earlier


def test_new_leaves_out_postings_already_held_and_a_usajobs_summary_has_no_calls_left():
    held = posting("1")
    deps, *_ = make_deps(results=[result([held, posting("2")], source=Source.usajobs, calls_left=None)])
    state = asked(search_call("Analyst", tool="search_usajobs"), search_plan=plan(country="us"), postings={held.key: held})

    update = run(make_nodes(deps)["tools"], state)

    content = update["messages"][-1].content
    assert "2 Postings, 1 new." in content and "calls left" not in content


def test_the_first_turn_holds_the_plan_goal_sample_and_only_matching_searches():
    same = record([posting("1")], title="data analyst", total=900)
    other_radius = record([posting("2")], title="analyst", the_plan=plan(radius_km=50))
    failed = record(title="bi analyst", error="down")
    state = dict(search_plan=plan(target_postings=40), fetches=[same, other_radius, failed], sample=["a:1"])

    update, cheap = fetch_agent_turn([ai_calls(search_call("Data Analyst"))], **state)

    system, human = cheap.seen[0]
    assert system.content.startswith("You gather job postings")
    assert plan(target_postings=40).model_dump_json() in human.content
    assert "about 60 Postings" in human.content and "Sample so far: 1 relevant" in human.content
    assert 'adzuna "data analyst" page 1: 900 matches' in human.content
    assert '"analyst" page' not in human.content.replace('"data analyst"', "") and "bi analyst" not in human.content
    assert update["messages"][-1].tool_calls and "run_log" not in update


def test_later_turns_send_the_messages_and_append_the_reply():
    history = [SystemMessage("s"), HumanMessage("h"), ai_calls(search_call("a")), ToolMessage(content="done", tool_call_id="c1")]
    reply = AIMessage(content="That is enough.")

    update, cheap = fetch_agent_turn([reply], messages=history)

    assert cheap.seen[0] == history
    assert update["messages"] == [*history, reply]


def test_a_turn_at_the_cap_makes_no_llm_call_and_writes_a_note():
    history = [ai_calls(search_call("a"))] + [ToolMessage(content="x", tool_call_id=str(i)) for i in range(MAX_FETCHES)]

    update, cheap = fetch_agent_turn([], messages=history)

    assert cheap.seen == [] and "messages" not in update
    assert update["run_log"][-1].kind == LogKind.note
    assert after_fetch_agent(state_with(messages=history)) == "collect"


def test_no_tool_call_on_the_first_turn_logs_a_warning_and_goes_to_collect():
    update, _ = fetch_agent_turn([AIMessage(content="Nothing to search.")])

    assert [e.kind for e in update["run_log"]] == [LogKind.warning]
    assert after_fetch_agent(state_with(messages=update["messages"])) == "collect"


def test_a_graph_loops_fetch_agent_tools_fetch_agent_then_collect():
    deps, *_, gateway = make_deps(
        cheap=[ai_calls(search_call("Data Analyst")), AIMessage(content="Enough.")],
        results=[result([posting("1")])],
    )
    nodes = make_nodes(deps)
    visited = []

    async def collect(state):
        visited.append("collect")
        return {}

    builder = StateGraph(State)
    for name, fn in {"fetch_agent": nodes["fetch_agent"], "tools": nodes["tools"], "collect": collect}.items():
        builder.add_node(name, fn)
    builder.add_edge(START, "fetch_agent")
    builder.add_edge("tools", "fetch_agent")
    builder.add_edge("collect", END)
    builder.add_conditional_edges("fetch_agent", after_fetch_agent, ["tools", "collect"])
    graph = builder.compile(checkpointer=InMemorySaver())

    final = asyncio.run(graph.ainvoke(state_with().model_dump(), {"configurable": {"thread_id": "t"}}))

    assert visited == ["collect"] and len(gateway.fetches) == 1
    assert [type(m).__name__ for m in final["messages"]] == ["SystemMessage", "HumanMessage", "AIMessage", "ToolMessage", "AIMessage"]
    assert len(final["fetches"]) == 1



def test_tools_emits_tool_called_and_tool_returned_for_a_good_call_and_a_failed_one():
    deps, *_ = make_deps(results=[result([posting("1"), posting("2")]), SourceUnavailable("adzuna is down")])
    graph = StateGraph(State).add_node("tools", make_nodes(deps)["tools"]).add_edge(START, "tools").add_edge("tools", END).compile()
    state = asked(search_call("Data Analyst", id="a"), search_call("Analyst", page=2, id="b"))

    async def go():
        return [c async for c in graph.astream(state.model_dump(), stream_mode="custom")]

    events = asyncio.run(go())

    assert sorted(e["summary"] for e in events if e["type"] == "tool_called") == ['"Analyst" page 2', '"Data Analyst" page 1']
    assert [e["summary"] for e in events if e["type"] == "tool_returned"] == ["2 Postings, 2 new", "Didn't run"]
    assert {e["name"] for e in events} == {"search_adzuna"}
