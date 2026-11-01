"""Write finished local Runs to samples/<name>/: the Brief, the questions and answers, and the routing trace.

Usage: uv run python scripts/export_samples.py NAME=THREAD_ID [NAME=THREAD_ID ...]
"""
import asyncio
import re
import shutil
import sys
from pathlib import Path

from talent_scout.kernel.settings import get_settings
from talent_scout.runtime.controller import RunController

OUT = Path("samples")


def transcript(request: str, notes: dict) -> str:
    lines = ["# Transcript", "", f"**Request:** {request}", "", "## Clarifying questions", ""]
    if not notes["questions"]:
        lines.append("None asked: the request was clear, so the Run went straight to planning.")
    for n, q in enumerate(notes["questions"], 1):
        lines += [f"{n}. **Agent:** {q['text']}"]
        lines += [f"   - Options offered: {', '.join(q['options'])}"] if q["options"] else []
        lines += [f"   - **You:** {q['answer'] or '(no answer)'}"]
    plan = notes["final_plan"]
    where = ", ".join(plan.get("locations") or [plan.get("location") or "country-wide"])
    lines += ["", "## Final search plan", "", f"- Titles: {', '.join(plan['titles'])}", f"- Where: {where} ({plan['country']}), radius {plan['radius_km']} km",
              f"- Posted within: {plan['max_days_old']} days", f"- Target postings: {plan['target_postings']}"]
    lines += ["", "## Assumptions", ""] + ([f"- {a['about']}: {a['value']} ({a['reason']})" for a in notes["assumptions"]] or ["None."])
    return "\n".join(lines) + "\n"


# The Steps of web/src/run/steps.ts, so the diagram matches the graph panel in the app.
STEPS = {
    "read": "Read your request", "ask": "Ask you", "plan": "Plan the search", "approve": "Your approval", "search": "Search job boards",
    "filter": "Filter postings", "widen": "Widen the search", "few": "Too few postings?", "postings": "Read postings",
    "normalise": "Tidy skill names", "stats": "Compute the numbers", "write": "Write the brief", "check": "Check every claim", "finish": "Finish",
}
STEP_OF = {
    "intake": "read", "clarity_check": "read", "clarify": "ask", "plan": "plan", "plan_review": "approve", "fetch_agent": "search", "tools": "search",
    "collect": "filter", "relevance": "filter", "broaden": "widen", "low_data_review": "few", "batch_extract": "postings",
    "normalise_skills": "normalise", "stats": "stats", "write_brief": "write", "critic": "check", "render": "finish",
}
# These two run without a log line of their own: fetching before collect, extracting before normalise.
IMPLIED = {"collect": "search", "normalise_skills": "postings"}


def trace(log) -> str:
    """A flowchart of the path the Run took: boxes are Steps, arrows are its moves, and a loop shows as a back arrow."""
    path: list[str] = []
    waited: set[str] = set()
    labels: dict[tuple[str, str], list[str]] = {}
    last_route: dict[str, str] = {}  # a Step's latest routing decision, which labels the arrow it leaves by

    def go(step: str) -> None:
        if path[-1:] != [step]:
            if path and path[-1] in last_route:
                labels.setdefault((path[-1], step), []).append(last_route.pop(path[-1]))
            path.append(step)

    for e in log:
        step = STEP_OF[e.node]
        if e.node in IMPLIED and path[-1] not in (IMPLIED[e.node], step):
            go(IMPLIED[e.node])
        go(step)
        if e.kind == "pause":
            waited.add(step)
        if e.kind == "route":
            last_route[step] = re.sub(r" \(route: (\w+)\)", r" → \1", e.message.replace('"', "'"))
    visits = {s: path.count(s) for s in dict.fromkeys(path)}
    edges: dict[tuple[str, str], int] = {}
    for pair in zip(path, path[1:]):
        edges[pair] = edges.get(pair, 0) + 1

    lines = ["flowchart TD"]
    for step, n in visits.items():
        lines.append(f'    {step}["{STEPS[step]}{f"<br/>×{n}" if n > 1 else ""}{"<br/>⏸ waited for you" if step in waited else ""}"]')
    for (a, b), n in edges.items():
        text = ((f"×{n} " if n > 1 else "") + "<br/>".join(dict.fromkeys(labels.get((a, b), [])))).strip()
        lines.append(f'    {a} -->|"{text}"| {b}' if text else f"    {a} --> {b}")
    lines.append(f"    class {','.join(visits)} done")
    if waited:
        lines.append(f"    class {','.join(waited)} paused")
    lines += ["    classDef done fill:#dbe8e3,stroke:#2f5d50,color:#1f2430", "    classDef paused fill:#f7e8d3,stroke:#8a4206,color:#1f2430"]
    unused = [name for step, name in STEPS.items() if step not in visits]
    return (
        "# Routing trace\n\nThe path the agent took. Green boxes are Steps it ran, amber boxes are where it stopped and waited for you, "
        "and a label on an arrow is the decision it made there. `×2` means that move happened twice.\n\n"
        "```mermaid\n" + "\n".join(lines) + "\n```\n"
        + (f"\nNot needed in this Run: {', '.join(unused)}.\n" if unused else "")
    )


async def main(pairs: list[str]) -> None:
    settings = get_settings().model_copy(update={"demo": True})  # demo deps: reads the saved Runs, calls no LLM or jobs API
    async with RunController.open(settings) as controller:
        for pair in pairs:
            name, thread_id = pair.split("=")
            view = await controller.get_run(thread_id)
            assert view.state and view.state.brief, f"{thread_id} has no Brief"
            folder = OUT / name
            shutil.rmtree(folder, ignore_errors=True)
            folder.mkdir(parents=True)
            for path in controller.brief_paths(thread_id):
                shutil.copy(path, folder / path.name)
            brief = view.state.brief.model_dump(mode="json")
            (folder / "transcript.md").write_text(transcript(view.state.request_text, brief["run_notes"]), encoding="utf-8")
            (folder / "trace.md").write_text(trace(view.state.run_log), encoding="utf-8")
            print(f"{folder}: {len(view.state.run_log)} log lines")


asyncio.run(main(sys.argv[1:]))
