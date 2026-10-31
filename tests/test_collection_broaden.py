import asyncio
import json
from datetime import UTC, date, datetime

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from talent_scout.collection.nodes import MAX_BROADENS, after_low_data, after_relevance, make_nodes
from talent_scout.collection.testing import ai_calls, make_deps, plan, posting, record, result, search_call, state_with
from talent_scout.gateway.types import CacheStatus, SourceUnavailable
from talent_scout.kernel.state import LogKind, State
from talent_scout.kernel.testing import fake_classifier
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
    assert update["run_log"][-1].message.startswith("broadened: ") and "radius_km: 25 -> 60" in update["run_log"][-1].message
    # The guidance used up here reached the prompt.
    assert "try BI roles" in strong.seen[0][1].content


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


def test_low_data_review_doesnt_interrupt_leaves_the_decision_null_and_logs_closing_caveats():
    deps, *_ = make_deps()
    update = run(make_nodes(deps)["low_data_review"], state_with())

    assert "low_data_decision" not in update
    assert "Too few Postings: 0 relevant of a target of 20" in caveats(update["run_log"])


# graph runs with the later stages stubbed


def collection_graph(deps, visited):
    nodes = make_nodes(deps)

    async def stats(state):
        visited.append(len(state.sample))
        return {}

    builder = StateGraph(State)
    for name in ("fetch_agent", "tools", "collect", "relevance", "broaden", "low_data_review"):
        builder.add_node(name, nodes[name])
    builder.add_node("stats", stats)
    builder.add_edge(START, "fetch_agent")
    builder.add_edge("tools", "fetch_agent")
    builder.add_edge("collect", "relevance")
    builder.add_edge("broaden", "fetch_agent")
    builder.add_edge("stats", END)
    builder.add_conditional_edges("fetch_agent", lambda s: "tools" if s.messages[-1].tool_calls else "collect", ["tools", "collect"])
    builder.add_conditional_edges("relevance", _with_fan_out(after_relevance), ["stats", "broaden", "low_data_review"])
    builder.add_conditional_edges("low_data_review", _with_fan_out(after_low_data), ["stats", "broaden", END])
    return builder.compile(checkpointer=InMemorySaver())


def invoke(graph, **state):
    return asyncio.run(graph.ainvoke(state_with(**state).model_dump(), {"configurable": {"thread_id": "t"}}))


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
def test_a_run_that_stays_short_gets_three_attempts_then_passes_through_to_stats(relevant, expected):
    deps, *_ = make_deps(
        cheap=[*attempt("a"), *attempt("b"), *attempt("c")],
        strong=[plan().model_dump_json()] * MAX_BROADENS,
        results=[pile(0, 5), result([]), result([])],
        classifier=fake_classifier({"relevant": relevant}),
    )
    visited = []

    final = invoke(collection_graph(deps, visited))

    assert visited == [expected] and len(final["broadened_plans"]) == MAX_BROADENS
    log = State.model_validate(final).run_log
    assert any(e.node == "low_data_review" and e.kind == LogKind.note for e in log)
    assert f"Too few Postings: {expected} relevant of a target of 20" in caveats(log)


def test_fetch_blocked_skips_straight_to_low_data_review_with_broadens_left():
    deps, _, strong, _ = make_deps(cheap=attempt("Data Analyst"), results=[SourceUnavailable("Adzuna is down")])
    visited = []

    final = invoke(collection_graph(deps, visited))

    assert visited == [0] and final["broadened_plans"] == [] and strong.seen == []
    assert final["fetch_blocked"] == "Every search in this Attempt failed: Adzuna is down"


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


def closing(posted: date, *, count: int = 20, **state):
    deps, *_ = make_deps()
    postings = {p.key: p for p in (posting(str(i), posted=posted, company=f"Co {i}") for i in range(count))}
    node = make_nodes(deps)["low_data_review"]
    return caveats(run(node, state_with(postings=postings, sample=list(postings), fetches=[record(fetched_at=datetime(2026, 1, 20, tzinfo=UTC))], **state))["run_log"])


def test_old_data_caveat_counts_over_half_older_than_30_days_from_the_newest_fetch_not_today():
    # Today is months after both fetch dates, so a clock-based rule would flag the second case too.
    assert closing(date(2025, 12, 1)) == ["Old data: 20 of 20 Postings are over 30 days old"]
    assert closing(date(2026, 1, 15)) == []


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
