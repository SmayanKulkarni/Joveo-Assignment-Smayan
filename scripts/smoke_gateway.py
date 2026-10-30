"""Live smoke test, not run in CI. Spends one Adzuna call (none if the same Fetch is still in L1)."""
import asyncio

from langsmith import Client

from talent_scout.gateway.gateway import make_gateway
from talent_scout.gateway.types import Fetch
from talent_scout.kernel.settings import get_settings


async def main():
    # Replay off, so the answer comes from the real API rather than a recorded file.
    s = get_settings().model_copy(update={"replay_cache": None})
    f = Fetch(title="data engineer", country="us", location="", radius_km=0, max_days_old=7, category=None)
    async with make_gateway(s) as gw:
        out = await gw.fetch(f)
    print("postings:", len(out.postings), "merged:", len(out.merged))
    for source, o in out.sources.items():
        print(source, o)
    print("failures:", out.failures)
    print("first:", out.postings[0].title, "|", out.postings[0].company, "|", out.postings[0].salary)

    await asyncio.sleep(5)  # let LangSmith ingest
    for r in Client().list_runs(project_name=s.langsmith_project, run_type="tool", limit=3):
        print(r.name, r.extra["metadata"], r.outputs, r.inputs)


if __name__ == "__main__":
    asyncio.run(main())
