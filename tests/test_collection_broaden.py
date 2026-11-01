import asyncio
import json
from datetime import UTC, date, datetime

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from talent_scout.analysis.types import ExtractBatch
from talent_scout.collection.nodes import MAX_BROADENS, after_low_data, after_relevance, make_nodes
from talent_scout.collection.testing import ai_calls, make_deps, plan, posting, record, result, search_call, state_with
from talent_scout.collection.types import LowDataAnswer
from talent_scout.gateway.types import CacheStatus, SourceUnavailable
from talent_scout.kernel.state import LogKind, State
from talent_scout.kernel.testing import fake_classifier
from talent_scout.kernel.types import Source
from talent_scout.runtime.graph import _with_fan_out


def run(node, state: State) -> dict:
    return asyncio.run(node(state))


def caveats(entries) -> list[str]:
    return [e.message for e in entries if e.kind == LogKind.caveat]


# broaden


def test_broaden_pins_country_and_target_clears_messages_and_logs_the_change():
    wider = plan(country="us", target_postings=100, radius_km=60, titles=["Data Analyst", "BI Analyst"])
    deps, _, strong, _ = make_deps(strong=[wider.model_dump_json()])
    state = state_with(messages=[HumanMessage("old")], low_data_guidance="try BI roles")

    update = run(make_nodes(deps)["broaden"], state)

    (new,) = update["broadened_plans"]
    assert (new.country, new.target_postings) == ("in", 20)
    assert new.radius_km == 60 and new.titles == ["Data Analyst", "BI Analyst"]
    assert update["messages"] == [] and update["low_data_guidance"] is None
    assert update["run_log"][-2].message.startswith("broadened: ") and "radius_km: 25 -> 60" in update["run_log"][-2].message
    # The guidance used up here reached the prompt.
    assert "try BI roles" in strong.seen[0][1].content


def test_broaden_keeps_the_place_unless_the_user_ticked_whole_country():
    drafted = plan(location="", radius_km=60).model_dump_json()
    for whole, kept in ((False, "Pune"), (True, "")):
        deps, *_ = make_deps(strong=[drafted])
        update = run(make_nodes(deps)["broaden"], state_with(search_plan=plan(location="Pune"), low_data_whole_country=whole))
        assert update["broadened_plans"][0].location == kept


def test_only_a_broaden_answer_can_carry_whole_country_and_an_old_checkpoint_loads_without_it():
    _, (final,) = review(state_with(), LowDataAnswer(action="broaden", whole_country=True))
    assert final["low_data_whole_country"] is True
    _, (final,) = review(state_with(), LowDataAnswer(action="continue", whole_country=True))
    assert final["low_data_whole_country"] is False
    old = state_with().model_dump()
    del old["low_data_whole_country"]
    assert State.model_validate(old).low_data_whole_country is False


def test_broaden_feeds_the_other_limits_back_and_a_corrected_plan_passes():
    bad = json.dumps(plan().model_dump() | {"radius_km": 500})
    good = plan(radius_km=80)
    deps, _, strong, _ = make_deps(strong=[bad, good.model_dump_json()])

    update = run(make_nodes(deps)["broaden"], state_with())

    assert update["broadened_plans"][0].radius_km == 80
    retry = strong.seen[1]
    assert "failed validation" in retry[-1].content and "radius_km" in retry[-1].content


def test_broaden_input_holds_totals_rejected_titles_and_the_sample_count():
    deps, _, strong, _ = make_deps(strong=[plan().model_dump_json()])
    noisy = posting("9", title="Data Entry Analyst")
    state = state_with(
        postings={noisy.key: noisy}, relevance_verdicts={noisy.key: False}, sample=[],
        fetches=[record(title="data analyst", total=3200, postings=[]), record(title="bi analyst", error="Adzuna is down")],
    )

    run(make_nodes(deps)["broaden"], state)

    text = strong.seen[0][1].content
    assert 'adzuna "data analyst" page 1: 3,200 matches' in text
    assert 'adzuna "bi analyst" page 1: failed: Adzuna is down' in text
    assert "- Data Entry Analyst" in text and "Sample: 0 relevant Postings, target 20." in text


# routing


@pytest.mark.parametrize(
    ("decision", "expected"),
    [("abort", END), ("broaden", "broaden"), ("continue", "analyse"), (None, "analyse")],
)
def test_after_low_data_outcomes(decision, expected):
    assert after_low_data(state_with(low_data_decision=decision)) == expected


# low_data_review


def review(state: State, *answers: LowDataAnswer):
    """Runs the node alone in a checkpointed graph; returns the Pause payload and the state after each answer."""
    deps, _, _, gateway = make_deps()
    gateway.left[Source.adzuna] = 7
    builder = StateGraph(State)
    builder.add_node("low_data_review", make_nodes(deps)["low_data_review"])
    builder.add_edge(START, "low_data_review")
    graph = builder.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "t"}}
    out = asyncio.run(graph.ainvoke(state.model_dump(), config))
    payload = out["__interrupt__"][0].value.payload
    return payload, [asyncio.run(graph.ainvoke(Command(resume=a), config)) for a in answers]


def test_the_pause_carries_the_counts_every_plan_tried_and_the_block_reason():
    first, second = plan(), plan(radius_km=60)
    a, b = posting("1"), posting("2", title="Data Entry")
    state = state_with(
        postings={a.key: a, b.key: b}, relevance_verdicts={a.key: True, b.key: False}, sample=[a.key],
        broadened_plans=[second], fetch_blocked="Adzuna is down",
    )

    payload, _ = review(state)

    assert (payload.count, payload.target, payload.attempts) == (1, 20, 2)
    assert (payload.fetched, payload.rejected, payload.calls_left, payload.blocked) == (2, 1, 7, "Adzuna is down")
    assert payload.plans == [first, second]


@pytest.mark.parametrize("action", ["broaden", "continue", "abort"])
def test_each_action_is_written_with_its_guidance_and_logged(action):
    _, (final,) = review(state_with(), LowDataAnswer(action=action, guidance="try BI roles"))

    assert (final["low_data_decision"], final["low_data_guidance"]) == (action, "try BI roles")
    assert any(e.kind == LogKind.pause for e in State.model_validate(final).run_log)


def test_closing_caveats_fire_only_on_continue():
    short = state_with(broadened_plans=[plan(radius_km=60)])
    for action, fires in (("continue", True), ("broaden", False), ("abort", False)):
        _, (final,) = review(short, LowDataAnswer(action=action))
        assert bool(caveats(State.model_validate(final).run_log)) is fires


# graph runs with the later stages stubbed


def collection_graph(deps, visited):
    nodes = make_nodes(deps)

    async def stats(state):
        visited.append(len(state.sample))
        return {}

    builder = StateGraph(State)
    for name in ("fetch_agent", "tools", "collect", "relevance", "broaden", "low_data_review"):
        builder.add_node(name, nodes[name])
    async def batch_extract(batch: ExtractBatch):
        return {}

    builder.add_node("stats", stats)
    builder.add_node("batch_extract", batch_extract)
    builder.add_edge(START, "fetch_agent")
    builder.add_edge("tools", "fetch_agent")
    builder.add_edge("collect", "relevance")
    builder.add_edge("broaden", "fetch_agent")
    builder.add_edge("batch_extract", "stats")
    builder.add_edge("stats", END)
    builder.add_conditional_edges("fetch_agent", lambda s: "tools" if s.messages[-1].tool_calls else "collect", ["tools", "collect"])
    builder.add_conditional_edges("relevance", _with_fan_out(after_relevance), ["batch_extract", "stats", "broaden", "low_data_review"])
    builder.add_conditional_edges("low_data_review", _with_fan_out(after_low_data), ["batch_extract", "stats", "broaden", END])
    return builder.compile(checkpointer=InMemorySaver())


def invoke(graph, **state):
    return asyncio.run(graph.ainvoke(state_with(**state).model_dump(), {"configurable": {"thread_id": "t"}}))


def answer(graph, action: str, guidance: str | None = None):
    config = {"configurable": {"thread_id": "t"}}
    return asyncio.run(graph.ainvoke(Command(resume=LowDataAnswer(action=action, guidance=guidance)), config))


def attempt(title: str):
    return [ai_calls(search_call(title)), AIMessage(content="Enough.")]


def pile(start: int, count: int):
    return result([posting(str(i), company=f"Co {i}") for i in range(start, start + count)])


def test_too_few_postings_broadens_then_reaches_sufficiency():
    deps, *_ = make_deps(
        cheap=[*attempt("Data Analyst"), *attempt("BI Analyst")],
        strong=[plan(titles=["Data Analyst", "BI Analyst"]).model_dump_json()],
        results=[pile(0, 5), pile(100, 20)],
    )
    visited = []

    final = invoke(collection_graph(deps, visited))

    assert visited == [25] and len(final["broadened_plans"]) == 1
    assert caveats([e for e in State.model_validate(final).run_log]) == [
        "Broadened 1 time(s): titles: ['Data Analyst'] -> ['Data Analyst', 'BI Analyst']"
    ]


@pytest.mark.parametrize(("relevant", "expected"), [(1.0, 5), (0.0, 0)])
def test_a_run_that_stays_short_gets_three_attempts_then_pauses_and_continue_reaches_stats(relevant, expected):
    deps, *_ = make_deps(
        cheap=[*attempt("a"), *attempt("b"), *attempt("c")],
        strong=[plan().model_dump_json()] * MAX_BROADENS,
        results=[pile(0, 5), result([]), result([])],
        classifier=fake_classifier({"relevant": relevant}),
    )
    visited = []
    graph = collection_graph(deps, visited)

    paused = invoke(graph)
    assert visited == [] and len(paused["broadened_plans"]) == MAX_BROADENS
    assert paused["__interrupt__"][0].value.payload.count == expected

    log = State.model_validate(answer(graph, "continue")).run_log
    assert visited == [expected]
    assert f"Too few Postings: {expected} relevant of a target of 20" in caveats(log)


def test_a_broaden_past_the_cap_returns_to_the_pause_and_its_guidance_reaches_the_broaden():
    deps, _, strong, _ = make_deps(
        cheap=[*attempt("a"), *attempt("b"), *attempt("c"), *attempt("d")],
        strong=[plan().model_dump_json()] * (MAX_BROADENS + 1),
        results=[result([])] * 4,
    )
    visited = []
    graph = collection_graph(deps, visited)
    invoke(graph)

    again = answer(graph, "broaden", "try BI roles")

    assert len(again["broadened_plans"]) == MAX_BROADENS + 1 and visited == []
    assert again["__interrupt__"][0].value.payload.attempts == MAX_BROADENS + 2
    assert "User guidance: try BI roles" in strong.seen[-1][1].content


def test_fetch_blocked_skips_straight_to_low_data_review_with_broadens_left():
    deps, _, strong, _ = make_deps(cheap=attempt("Data Analyst"), results=[SourceUnavailable("Adzuna is down")])
    visited = []
    graph = collection_graph(deps, visited)

    paused = invoke(graph)

    assert visited == [] and paused["broadened_plans"] == [] and strong.seen == []
    assert paused["fetch_blocked"] == "Every search in this Attempt failed: Adzuna is down"
    assert paused["__interrupt__"][0].value.payload.blocked == paused["fetch_blocked"]
    answer(graph, "continue")
    assert visited == [0]


# Caveats


def collected(fetches):
    deps, *_ = make_deps()
    return run(make_nodes(deps)["collect"], state_with(fetches=fetches))["run_log"]


def test_dropped_caveat_fires_only_when_the_mapper_dropped_something():
    assert caveats(collected([record([posting("1")], dropped=3)])) == ["3 Postings were dropped by the source mapper"]
    assert caveats(collected([record([posting("1")], dropped=0)])) == []


def test_replay_age_caveat_names_the_oldest_fetch_and_live_calls_and_a_normal_l2_read_raises_none():
    old = datetime(2026, 1, 1, tzinfo=UTC)
    replayed = [
        record([posting("1")], cache=CacheStatus.replay, fetched_at=old),
        record([posting("2")], title="b", cache=CacheStatus.miss),
    ]
    assert caveats(collected(replayed)) == [f"Replayed data: oldest fetched {old.isoformat()}, 1 live calls during replay"]
    assert caveats(collected([record([posting("1")], cache=CacheStatus.hit)])) == []


def test_jev_degraded_caveat_fires_on_a_truncated_verdict_and_not_on_a_normal_one():
    deps, *_ = make_deps()
    huge = posting("1", description="word " * 10_000)
    update = run(make_nodes(deps)["relevance"], state_with(postings={huge.key: huge}))
    assert any(m.startswith("Jev degraded: 1 Postings") for m in caveats(update["run_log"]))

    normal = posting("2")
    update = run(make_nodes(deps)["relevance"], state_with(postings={normal.key: normal}))
    assert not any(m.startswith("Jev degraded") for m in caveats(update["run_log"]))


def closing(posted: date, *, count: int = 20, source: Source = Source.adzuna, **state):
    postings = {p.key: p for p in (posting(str(i), posted=posted, source=source, company=f"Co {i}") for i in range(count))}
    start = state_with(postings=postings, sample=list(postings), fetches=[record(fetched_at=datetime(2026, 1, 20, tzinfo=UTC))], **state)
    _, (final,) = review(start, LowDataAnswer(action="continue"))
    return caveats(State.model_validate(final).run_log)


def test_old_data_caveat_counts_over_half_older_than_30_days_from_the_newest_fetch_not_today():
    # Today is months after both fetch dates, so a clock-based rule would flag the second case too.
    assert closing(date(2025, 12, 1)) == ["Old data: 20 of 20 Postings are over 30 days old"]
    assert closing(date(2026, 1, 15)) == []


def test_mostly_federal_caveat_fires_over_half_usajobs_and_not_for_private_postings():
    assert closing(date(2026, 1, 15), source=Source.usajobs) == ["Mostly federal: 20 of 20 Postings are from USAJOBS"]
    assert closing(date(2026, 1, 15)) == []


def test_one_source_failed_fires_on_a_partial_l2_page_or_a_failed_call_beside_an_answered_one():
    partial = record([posting("1")], failures={Source.usajobs: "USAJOBS is down"})
    assert caveats(collected([partial])) == ["One source failed: usajobs"]

    mixed = [record([posting("1")]), record(title="b", source=Source.usajobs, error="USAJOBS is down")]
    assert caveats(collected(mixed)) == ["One source failed: usajobs"]

    # Nothing failed, or everything failed: the second is a block for the Pause, not a Caveat.
    assert caveats(collected([record([posting("1")])])) == []
    assert caveats(collected([record(error="Adzuna is down")])) == []


def test_broadened_and_too_few_caveats_fire_only_when_true():
    assert closing(date(2026, 1, 15)) == []
    short = closing(date(2026, 1, 15), count=3, broadened_plans=[plan(radius_km=60)])
    assert short == ["Broadened 1 time(s): radius_km: 25 -> 60", "Too few Postings: 3 relevant of a target of 20"]


def test_closing_caveats_run_in_relevance_only_when_sufficient():
    deps, *_ = make_deps()
    many = {p.key: p for p in (posting(str(i), posted=date(2025, 12, 1), company=f"Co {i}") for i in range(20))}
    sufficient = run(make_nodes(deps)["relevance"], state_with(postings=many, fetches=[record()]))
    assert any(m.startswith("Old data") for m in caveats(sufficient["run_log"]))

    few = run(make_nodes(deps)["relevance"], state_with(postings={k: many[k] for k in list(many)[:3]}, fetches=[record()]))
    assert not any(m.startswith(("Old data", "Too few")) for m in caveats(few["run_log"]))
