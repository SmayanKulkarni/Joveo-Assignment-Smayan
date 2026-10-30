"""Live smoke test, not run in CI. Runs Request & Plan on the spec's cases with the real models, other stages stubbed."""
import asyncio
import sys

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.types import Command

from talent_scout.gateway.testing import FakeGateway
from talent_scout.kernel.jev import make_jev
from talent_scout.kernel.llm import make_tiers
from talent_scout.kernel.settings import get_settings
from talent_scout.kernel.state import State
from talent_scout.runtime.deps import Deps
from talent_scout.runtime.graph import build_graph
from talent_scout.runtime.pause import ALLOWED_MSGPACK, ANSWERS
from talent_scout.runtime.testing import ANSWER_FOR

# What a user would plausibly say to a question about each field.
ANSWERS_BY_FIELD = {"role": "Software engineer", "location": "Austin, Texas", "seniority": "5+ years"}


async def run_case(deps: Deps, request: str) -> State:
    saver = InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=ALLOWED_MSGPACK))
    graph = build_graph(deps, saver)
    config = {"configurable": {"thread_id": request}}
    command = {"request_text": request}
    while True:
        await graph.ainvoke(command, config)
        snapshot = await graph.aget_state(config)
        if not snapshot.interrupts:
            return State.model_validate(snapshot.values)
        pause = snapshot.interrupts[0].value
        if pause.kind == "clarify":
            for q in pause.payload.questions:
                print(f"  asked [{q.about.value}]: {q.text} {q.options}")
            answer = {"answers": [ANSWERS_BY_FIELD[q.about.value] for q in pause.payload.questions]}
        else:
            answer = ANSWER_FOR[pause.kind]
        command = Command(resume=ANSWERS[pause.kind].model_validate(answer))


async def main():
    # Both tiers pinned to one model so the spend stays at cents; pass a model id to check another chain model.
    model = [sys.argv[1] if len(sys.argv) > 1 else "minimax/minimax-m3.1-flash"]
    settings = get_settings().model_copy(update={"llm_cheap": model, "llm_strong": model})
    tiers = make_tiers(settings)
    deps = Deps(tiers, make_jev(settings, tiers), FakeGateway([]), settings)
    for request in ("Data Analyst, Bangalore", "Engineer, Texas"):
        print(request)
        state = await run_case(deps, request)
        for entry in state.run_log:
            if entry.node in ("intake", "clarity_check", "plan"):
                print(f"  {entry.node} [{entry.kind}] {entry.message} {entry.data if entry.kind == 'route' else ''}")
        print("  request:", state.hiring_request)
        print("  assumptions:", state.assumptions)
        print("  plan:", state.search_plan)


if __name__ == "__main__":
    asyncio.run(main())
