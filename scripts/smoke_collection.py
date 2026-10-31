"""Live smoke test, not run in CI. Spends a few Adzuna calls (at most 18) and cents on the model.

Runs "Data Analyst, Bangalore" through Request & Plan and Collection with the real models and Adzuna, later stages stubbed.
"""
import asyncio
import sys

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.types import Command

from talent_scout.collection.nodes import RAW_FACTOR
from talent_scout.gateway.gateway import make_gateway
from talent_scout.kernel.jev import make_jev
from talent_scout.kernel.llm import make_tiers
from talent_scout.kernel.settings import get_settings
from talent_scout.kernel.state import State
from talent_scout.runtime.deps import Deps
from talent_scout.runtime.graph import build_graph
from talent_scout.runtime.pause import ALLOWED_MSGPACK, ANSWERS
from talent_scout.runtime.testing import ANSWER_FOR

REQUEST = "Data Analyst, Bangalore"


async def main():
    # Both tiers pinned to one model so the spend stays at cents; replay off so Adzuna is really called.
    model = [sys.argv[1] if len(sys.argv) > 1 else "minimax/minimax-m3.1-flash"]
    settings = get_settings().model_copy(update={"llm_cheap": model, "llm_strong": model, "replay_cache": None})
    tiers = make_tiers(settings)
    async with make_gateway(settings) as gateway:
        graph = build_graph(Deps(tiers, make_jev(settings, tiers), gateway, settings), InMemorySaver(
            serde=JsonPlusSerializer(allowed_msgpack_modules=ALLOWED_MSGPACK)
        ))
        config = {"configurable": {"thread_id": REQUEST}}
        command = {"request_text": REQUEST}
        while True:
            await graph.ainvoke(command, config)
            snapshot = await graph.aget_state(config)
            if not snapshot.interrupts:
                break
            kind = snapshot.interrupts[0].value.kind
            command = Command(resume=ANSWERS[kind].model_validate(ANSWER_FOR[kind]))

    state = State.model_validate(snapshot.values)
    for e in state.run_log:
        if e.node in ("fetch_agent", "collect", "relevance", "broaden", "low_data_review"):
            print(f"{e.node} [{e.kind}] {e.message}")
    raw = len(state.postings)
    target = state.current_plan.target_postings
    print(f"\nAttempts: {len(state.broadened_plans) + 1}, plan titles: {state.current_plan.titles}")
    print(f"Raw {raw} vs {RAW_FACTOR} x target {round(RAW_FACTOR * target)}; relevant {len(state.sample)} of {raw} (target {target})")
    print(f"Relevance rate: {len(state.sample) / raw:.0%}" if raw else "No Postings fetched")
    # Rejected titles are what shows whether the 0.5 cut is too strict or too loose.
    print("Rejected titles:", [p.title for k, p in state.postings.items() if not state.relevance_verdicts[k]][:10])
    print("Closing Caveats:", [e.message for e in state.run_log if e.kind == "caveat"])


if __name__ == "__main__":
    asyncio.run(main())
