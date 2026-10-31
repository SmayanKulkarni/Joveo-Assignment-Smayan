"""Live smoke test, not run in CI. Spends no job API calls, only cents on the model.

Runs the recorded fixture Postings through Analysis (extract, merge skills, stats) with the real model and prints the result.
"""
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from talent_scout.analysis.nodes import fan_out, make_nodes
from talent_scout.analysis.stats import fold
from talent_scout.gateway.adzuna import _map as map_adzuna
from talent_scout.gateway.usajobs import _map as map_usajobs
from talent_scout.kernel.llm import make_tiers
from talent_scout.kernel.settings import get_settings
from talent_scout.kernel.state import LogKind, State
from talent_scout.kernel.types import HiringRequest, SearchPlan

FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures" / "jobs"
sys.stdout.reconfigure(encoding="utf-8")  # merges print an arrow the Windows console can't encode
# Pairs the merge prompt must keep apart whenever both show up in the Sample.
MUST_STAY_APART = [("AWS", "S3"), ("Git", "GitLab")]


def load_postings():
    def body(name):
        return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))["body"]

    raw = [r for name in ("adzuna_search", "adzuna_search_dc") for r in body(name)["results"]]
    federal = body("usajobs_search")["SearchResult"]["SearchResultItems"]
    postings = [*(map_adzuna(r, "us") for r in raw), *(map_usajobs(i) for i in federal)]
    return {p.key: p for p in postings}


def initial_state() -> State:
    postings = load_postings()
    request = HiringRequest(
        role="Data Engineer", location="United States", country="us", seniority=None, employment_type=None,
        work_mode=None, currency=None, purpose=None,
    )
    plan = SearchPlan(
        titles=["Data Engineer"], country="us", location="United States", radius_km=25, max_days_old=30,
        target_postings=len(postings), category=None,
    )
    return State(
        request_text="Data Engineer, United States", hiring_request=request, search_plan=plan,
        postings=postings, sample=sorted(postings),
    )


async def run_analysis(state: State, model: str) -> State:
    # Both tiers pinned to one model so the spend stays at cents; replay off so the model is really called.
    settings = get_settings().model_copy(update={"llm_cheap": [model], "llm_strong": [model], "replay_cache": None})
    # Analysis only touches deps.tiers, so Jev and the Gateway are left out.
    nodes = make_nodes(SimpleNamespace(tiers=make_tiers(settings)))

    sends = fan_out(state)
    print(f"{len(state.sample)} Postings in {len(sends)} Batches")
    updates = await asyncio.gather(*(nodes["batch_extract"](s.arg) for s in sends))
    for send, update in zip(sends, updates):
        if not update:  # batch_extract returns {} when the model's output was unusable
            print(f"Batch of {len(send.arg.postings)} Postings returned no Extractions")
    state = state.model_copy(update={"extractions": {k: e for u in updates for k, e in u.get("extractions", {}).items()}})
    state = state.model_copy(update=await nodes["normalise_skills"](state))
    return state.model_copy(update=await nodes["stats"](state))


def check_stay_apart(state: State) -> None:
    seen = {fold(s.name) for e in state.extractions.values() for s in e.skills}

    def resolved(name: str) -> str:
        folded = fold(name)
        return fold(state.skill_aliases.get(folded, folded))

    for a, b in MUST_STAY_APART:
        if {fold(a), fold(b)} <= seen:
            assert resolved(a) != resolved(b), f"{a} and {b} were merged: {state.skill_aliases}"
            print(f"OK: {a} and {b} both appear and stay apart")
        else:
            print(f"Not checked: {a} and {b} do not both appear")


async def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "minimax/minimax-m3.1-flash"
    state = await run_analysis(initial_state(), model)

    extracted = len(state.extractions)
    print(f"Extracted {extracted} of {len(state.sample)}; skills dropped as ungrounded: {sum(e.ungrounded for e in state.extractions.values())}")

    print("\nTop skills:")
    for s in state.stats.stats:
        if s.id.startswith("skills.") and s.id.endswith(".count"):
            print(f"  {s.label}")

    merges = [e.message for e in state.run_log if e.node == "normalise_skills"]
    print("\nMerges:", *merges, sep="\n  ")

    print("\nEmployer types:")
    for s in state.stats.stats:
        if s.id.startswith("competition.") and s.id.endswith("_share"):
            print(f"  {s.label}")

    print("\nCaveats:", *(e.message for e in state.run_log if e.kind == LogKind.caveat), sep="\n  ")
    print("\nStats note:", next(e.message for e in reversed(state.run_log) if e.node == "stats" and e.kind == LogKind.note))

    print()
    check_stay_apart(state)


if __name__ == "__main__":
    asyncio.run(main())
