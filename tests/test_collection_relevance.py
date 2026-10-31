import asyncio
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from talent_scout.analysis.types import ExtractBatch
from talent_scout.collection.nodes import MAX_BROADENS, after_relevance, make_nodes
from talent_scout.collection.testing import make_deps, plan, posting, record, result, search_call, ai_calls, state_with
from talent_scout.gateway.types import CacheStatus
from talent_scout.kernel.state import LogKind, State
from talent_scout.kernel.testing import FakeClassifier
from talent_scout.kernel.types import Source
from talent_scout.runtime.graph import _with_fan_out


def run(node, state: State) -> dict:
    return asyncio.run(node(state))


class TitleClassifier(FakeClassifier):
    """Says no to any title containing 'Entry', so verdicts differ per Posting."""

    def invoke(self, input, config=None, **kwargs):
        self.answers = {"relevant": 0.0 if "Entry" in input["state"]["title"] else 1.0}
        return super().invoke(input, config)


def title_classifier() -> TitleClassifier:
    return TitleClassifier({}, "typesafe/jev-1.14-20260101", [])


def notes(update: dict, message: str):
    return next(e for e in update["run_log"] if e.message.startswith(message))


# collect


def test_the_same_key_from_two_attempts_stays_one_posting_with_no_self_merge():
    held = posting("1", description="the first copy seen has these words in it")
    again = posting("1", description="a later copy with different words altogether")
    deps, *_ = make_deps()
    state = state_with(
        broadened_plans=[plan()], postings={held.key: held},
        fetches=[record([again, posting("2", company="Other Co")], attempt=1)],
    )

    update = run(make_nodes(deps)["collect"], state)

    assert set(update["postings"]) == {held.key, "adzuna:2"}
    assert update["postings"][held.key].description == held.description
    assert notes(update, "kept").data["duplicates"] == 0


def test_a_duplicate_across_fetches_collapses():
    deps, *_ = make_deps()
    twin = dict(company="Acme", description="same advert text posted twice by one employer today")
    state = state_with(fetches=[record([posting("1", **twin)], title="a"), record([posting("2", **twin)], title="b")])

    update = run(make_nodes(deps)["collect"], state)

    assert list(update["postings"]) == ["adzuna:1"]
    entry = notes(update, "kept")
    assert (entry.kind, entry.data) == (LogKind.note, {"kept": 1, "duplicates": 1})


def test_records_lose_their_postings_but_keep_totals_and_store_totals_are_left_out():
    deps, *_ = make_deps()
    state = state_with(fetches=[
        record([posting("1")], title="data analyst", total=3200),
        record([posting("2")], title="bi analyst", source=Source.usajobs, cache=CacheStatus.store, total=40),
        record(title="broken", error="Adzuna is down"),
    ])

    update = run(make_nodes(deps)["collect"], state)

    kept = update["fetches"]
    assert [r.result.postings if r.result else None for r in kept] == [[], [], None]
    assert kept[0].result.sources[Source.adzuna].total == 3200 and kept[2].error == "Adzuna is down"
    assert notes(update, "source totals").data["totals"] == {"data analyst": {"adzuna": 3200}}


# relevance


def test_only_unjudged_postings_are_sent_and_the_sample_drops_a_merged_key():
    classifier = title_classifier()
    deps, *_ = make_deps(classifier=classifier)
    a, b, entry = posting("1"), posting("2"), posting("3", title="Data Entry Analyst")
    state = state_with(postings={p.key: p for p in (a, b, entry)}, relevance_verdicts={a.key: True, "adzuna:gone": True})

    update = run(make_nodes(deps)["relevance"], state)

    assert [c["state"]["title"] for c in classifier.calls] == ["Data Analyst", "Data Entry Analyst"]
    sent = classifier.calls[0]["state"]
    assert sent["role"] == "Data Analyst" and sent["seniority"] == "Senior" and sent["company"] == "Company 2"
    # A kept verdict for a key coalesce merged away must not leak into the Sample.
    assert update["sample"] == [a.key, b.key]
    assert update["relevance_verdicts"][entry.key] is False


def test_the_route_log_names_the_count_and_outcome():
    deps, *_ = make_deps()
    state = state_with(postings={"adzuna:1": posting("1")})

    update = run(make_nodes(deps)["relevance"], state)

    (route,) = [e for e in update["run_log"] if e.kind == LogKind.route]
    assert route.message == "1 of 1 Postings relevant (route: broaden)"


def blocked_after(*, current=None, left=None, replay=False, **plan_over) -> str | None:
    deps, *_, gateway = make_deps(**({"replay_cache": Path("r")} if replay else {}))
    gateway.left[Source.adzuna] = left
    state = state_with(search_plan=plan(**plan_over), fetches=current or [])
    return run(make_nodes(deps)["relevance"], state)["fetch_blocked"]


def test_both_fetch_blocked_reasons_fire():
    failed = [record(title="a", error="Adzuna is down"), record(title="b", error="Adzuna is down")]
    assert blocked_after(current=failed) == "Every search in this Attempt failed: Adzuna is down"
    # One answering search means the Attempt isn't all-failed.
    assert blocked_after(current=[*failed, record([posting("1")])]) is None
    assert blocked_after(left=0) == "Adzuna's daily limit is used up, until the next UTC day"
    assert blocked_after(left=3) is None


def test_a_us_run_isnt_blocked_by_an_empty_adzuna_budget_and_replay_skips_the_check():
    assert blocked_after(left=0, country="us") is None
    assert blocked_after(left=0, replay=True) is None


# routing


@pytest.mark.parametrize(
    ("sample", "blocked", "broadens", "expected"),
    [
        (20, None, 0, "analyse"),
        (25, "blocked", MAX_BROADENS, "analyse"),
        (3, "Adzuna's daily limit is used up, until the next UTC day", 0, "low_data_review"),
        (3, None, MAX_BROADENS, "low_data_review"),
        (3, None, MAX_BROADENS - 1, "broaden"),
        (19, None, 0, "broaden"),
    ],
)
def test_after_relevance_outcomes(sample, blocked, broadens, expected):
    state = state_with(
        sample=[f"adzuna:{i}" for i in range(sample)], fetch_blocked=blocked, broadened_plans=[plan()] * broadens
    )
    assert after_relevance(state) == expected


def test_a_sufficient_first_attempt_goes_from_fetch_agent_to_stats():
    deps, *_ = make_deps(
        cheap=[ai_calls(search_call("Data Analyst")), AIMessage(content="Enough.")],
        results=[result([posting(str(i), company=f"Co {i}") for i in range(20)], total=20)],
    )
    nodes = make_nodes(deps)
    visited = []

    async def stats(state):
        visited.append("stats")
        return {}

    builder = StateGraph(State)
    for name in ("fetch_agent", "tools", "collect", "relevance"):
        builder.add_node(name, nodes[name])
    async def batch_extract(batch: ExtractBatch):
        return {}

    builder.add_node("stats", stats)
    builder.add_node("batch_extract", batch_extract)
    builder.add_edge(START, "fetch_agent")
    builder.add_edge("tools", "fetch_agent")
    builder.add_edge("collect", "relevance")
    builder.add_edge("batch_extract", "stats")
    builder.add_edge("stats", END)
    builder.add_conditional_edges("fetch_agent", lambda s: "tools" if s.messages[-1].tool_calls else "collect", ["tools", "collect"])
    # The same wrapper build_graph applies, with Analysis's real fan_out and a stub branch.
    builder.add_conditional_edges("relevance", _with_fan_out(after_relevance), ["batch_extract", "stats"])
    graph = builder.compile(checkpointer=InMemorySaver())

    final = asyncio.run(graph.ainvoke(state_with(search_plan=plan(target_postings=20)).model_dump(), {"configurable": {"thread_id": "t"}}))

    assert visited == ["stats"] and len(final["sample"]) == 20
