"""Live smoke test, not run in CI. Spends cents on z-ai/glm-5.3-flash."""
import asyncio

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_typesafe import Noul
from langsmith import Client
from pydantic import BaseModel, Field

from talent_scout.kernel.jev import llm_fallback, make_jev
from talent_scout.kernel.llm import check_balance, make_tiers
from talent_scout.kernel.settings import get_settings


class Capital(BaseModel):
    city: str = Field(description="Capital city name.")
    country: str = Field(description="Country the city is the capital of.")


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return "sunny"


async def main():
    s = get_settings()
    # Both tiers pinned to the cheap smoke model so the spend stays at cents.
    s = s.model_copy(update={"llm_cheap": ["z-ai/glm-5.3-flash"], "llm_strong": ["z-ai/glm-5.3-flash"]})
    print("balance:", await check_balance(s))
    tiers = make_tiers(s)
    for tier in ("cheap", "strong"):
        out = await tiers.structured(tier, Capital, system="Answer the question.", name=f"smoke_{tier}").ainvoke(
            "What is the capital of France?"
        )
        print(tier, out)
    msg = await tiers.chat("cheap", tools=[get_weather], name="smoke_chat").ainvoke(
        [HumanMessage("What is the weather in Paris? Use the tool.")]
    )
    print("tool_calls:", msg.tool_calls)
    print("usage:", msg.usage_metadata)

    questions = {"software": Noul(instructions="Is this job in software engineering?")}
    state = {"title": "Senior Python Developer"}
    jev = make_jev(s, tiers)
    print("jev:", await jev.judge("relevance", state, questions))
    # Call the adapter directly, since the real Jev is up and would never reach it.
    fallback = await llm_fallback(tiers).ainvoke({"state": state, "questions": questions})
    print("fallback:", fallback.model, fallback.nouls, fallback.reasons)

    await asyncio.sleep(5)  # let LangSmith ingest
    runs = Client().list_runs(project_name=s.langsmith_project, run_type="llm", limit=6)
    for r in runs:
        print(r.name, r.total_cost, r.prompt_cost, r.completion_cost, r.tags)


if __name__ == "__main__":
    asyncio.run(main())
