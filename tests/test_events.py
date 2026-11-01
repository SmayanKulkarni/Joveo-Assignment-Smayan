import asyncio
import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessageChunk
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from talent_scout.kernel.events import emit
from talent_scout.kernel.state import LogKind, State, log_entry, owned
from talent_scout.runtime.events import (
    ApiCalled, ChunkMapper, ExtractProgress, NodeDone, NodeStarted, Reasoning, Token, ToolCalled, ToolReturned,
)


def test_emit_is_a_no_op_outside_a_graph():
    emit({"type": "api_called"})


def test_emit_is_delivered_inside_a_graph_and_through_owned():
    async def node(state):
        emit({"type": "tool_called", "name": "x", "summary": "y"})
        return {}

    graph = StateGraph(State).add_node("fetch_agent", owned("fetch_agent", "collection")(node))
    graph.add_edge(START, "fetch_agent").add_edge("fetch_agent", END)

    async def go():
        return [c async for c in graph.compile().astream({"request_text": "x"}, stream_mode="custom")]

    assert asyncio.run(go()) == [{"type": "tool_called", "name": "x", "summary": "y"}]


def test_custom_dicts_map_to_events_and_unknown_types_are_dropped(caplog):
    mapper = ChunkMapper(0)
    assert mapper.map("custom", {"type": "tool_called", "name": "search", "summary": "q"}) == [ToolCalled(name="search", summary="q")]
    assert mapper.map("custom", {"type": "tool_returned", "name": "search", "summary": "2 Postings"}) == [
        ToolReturned(name="search", summary="2 Postings")
    ]
    api = {"type": "api_called", "source": "adzuna", "cached": True, "count": 3, "failed": False}
    assert mapper.map("custom", api) == [ApiCalled(source="adzuna", cached=True, count=3)]
    assert mapper.map("custom", {"type": "mystery"}) == []
    assert "mystery" in caplog.text


def test_node_done_results_are_only_the_result_lines():
    log = [log_entry("collect", LogKind.note, "source totals"), log_entry("collect", LogKind.result, "Found 80 postings")]
    (done,) = ChunkMapper(0).map("updates", {"collect": {"run_log": log}})
    assert done == NodeDone(node="collect", notes=["source totals", "Found 80 postings"], results=["Found 80 postings"])


def test_reasoning_comes_from_any_node_but_batch_extract_and_text_only_counts_as_a_token_in_fetch_agent():
    def chunk(node, *blocks):
        return AIMessageChunk(content=list(blocks)), {"langgraph_node": node}

    thought, text = {"type": "reasoning", "reasoning": "hmm"}, {"type": "text", "text": "hi"}
    mapper = ChunkMapper(0)
    assert mapper.map("messages", chunk("plan", thought, text)) == [Reasoning(node="plan", text="hmm")]
    assert mapper.map("messages", chunk("batch_extract", thought, text)) == []
    assert mapper.map("messages", chunk("fetch_agent", text)) == [Token(node="fetch_agent", text="hi")]
    # A turn with no reasoning is normal.
    assert mapper.map("messages", chunk("fetch_agent")) == []


class Fan(TypedDict):
    out: Annotated[list, operator.add]


def fan_out_graph(failing_branch):
    """Three batch_extract branches, one of which raises until `failing_branch` is emptied."""

    async def fan(state):
        return {}

    async def batch_extract(payload):
        if payload["k"] in failing_branch:
            failing_branch.clear()
            raise ValueError("boom")
        return {"out": [payload["k"]]}

    graph = StateGraph(Fan).add_node("fan", fan).add_node("batch_extract", batch_extract)
    graph.add_edge(START, "fan").add_edge("batch_extract", END)
    graph.add_conditional_edges("fan", lambda s: [Send("batch_extract", {"k": k}) for k in "abc"], ["batch_extract"])
    return graph.compile(checkpointer=MemorySaver())


def test_a_failing_send_branch_is_counted_correctly_across_the_rerun():
    graph = fan_out_graph(failing_branch=["b"])
    config = {"configurable": {"thread_id": "t"}}

    async def stream(graph_input):
        mapper, events = ChunkMapper(0), []
        try:
            async for mode, chunk in graph.astream(graph_input, config, stream_mode=["updates", "tasks"]):
                events += mapper.map(mode, chunk)
        except ValueError:
            pass
        return events

    async def go():
        return await stream({"out": []}), await stream(None)

    first, rerun = asyncio.run(go())

    assert first == [
        NodeStarted(node="fan"), NodeDone(node="fan", notes=[]), NodeStarted(node="batch_extract"),
        ExtractProgress(done=1, total=3), ExtractProgress(done=2, total=3),
    ]
    # Finished branches come back cached, so the rerun still counts to 3 and finishes the node once.
    assert rerun == [
        NodeStarted(node="batch_extract"), ExtractProgress(done=1, total=3), ExtractProgress(done=2, total=3),
        ExtractProgress(done=3, total=3), NodeDone(node="batch_extract", notes=[]),
    ]
