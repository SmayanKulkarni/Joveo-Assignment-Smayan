import asyncio

import aiosqlite
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START
from langgraph.types import Command

from talent_scout.brief.types import MarketBrief
from talent_scout.kernel.state import State
from talent_scout.kernel.testing import make_settings
from talent_scout.kernel.types import ClarifyingQuestion, RequestField
from talent_scout.runtime.graph import OWNERS, build_graph
from talent_scout.runtime.pause import ALLOWED_MSGPACK, ANSWERS, ClarifyPause, LowDataPause, PlanReviewPause
from talent_scout.runtime.registry import RunStatus, derive_status
from talent_scout.runtime.testing import fake_deps

ANSWER_FOR = {
    "clarify": {"answers": ["Software"]},
    "plan_review": {"action": "approve", "plan": None, "feedback": None},
    "low_data_review": {"action": "continue"},
}


def test_full_graph_compiles_with_every_owned_node():
    graph = build_graph(fake_deps(make_settings()), None)
    assert set(graph.get_graph().nodes) == {START, END} | {n for names in OWNERS.values() for n in names}


def test_stub_run_reaches_render_through_all_three_pauses(tmp_path):
    async def go():
        async with aiosqlite.connect(tmp_path / "runs.sqlite") as conn:
            saver = AsyncSqliteSaver(conn, serde=JsonPlusSerializer(allowed_msgpack_modules=ALLOWED_MSGPACK))
            await saver.setup()
            graph = build_graph(fake_deps(make_settings()), saver)
            config = {"configurable": {"thread_id": "t1"}}

            pauses = []
            command = {"request_text": "Engineer, Texas"}
            while True:
                # A real Run goes through astream with these modes, so the stubs must hold up under them.
                async for _ in graph.astream(
                    command, config, durability="sync", stream_mode=["updates", "messages", "custom", "tasks"]
                ):
                    pass
                snapshot = await graph.aget_state(config)
                if not snapshot.interrupts:
                    return pauses, snapshot
                pause = snapshot.interrupts[0].value
                pauses.append(pause)
                command = Command(resume=ANSWERS[pause.kind].model_validate(ANSWER_FOR[pause.kind]))

    pauses, snapshot = asyncio.run(go())

    assert [type(p) for p in pauses] == [ClarifyPause, PlanReviewPause, LowDataPause]
    # Enum inside a payload: read back from sqlite, so a checkpoint keeps it typed.
    question = pauses[0].payload.questions[0]
    assert isinstance(question, ClarifyingQuestion) and question.about is RequestField.role

    state = State.model_validate(snapshot.values)
    assert [e.node for e in state.run_log] == [
        "intake", "clarity_check", "clarify", "intake", "clarity_check", "plan", "plan_review", "fetch_agent",
        "collect", "relevance", "low_data_review", "stats", "write_brief", "critic", "render",
    ]
    assert state.questions[0].answer == "Software"
    assert state.brief == MarketBrief()
    assert state.brief_markdown
    assert derive_status(snapshot) == (RunStatus.done, None)
