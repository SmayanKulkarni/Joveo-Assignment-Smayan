from collections import Counter

from talent_scout.brief.rules import SOURCE_NAMES
from talent_scout.brief.types import MarketBrief
from talent_scout.kernel.types import Posting, SearchPlan

REPLAY_BANNER = "Replayed run: jobs data, LLM and Jev responses came from the replay cache, not live sources"
NO_RECOMMENDATIONS = (
    "Not enough evidence to suggest a job title.",
    "Not enough evidence to suggest a salary band.",
    "Not enough evidence to suggest top skills.",
)


def _plan(p: SearchPlan) -> str:
    return (
        f"titles {', '.join(p.titles)}; location {p.location or 'country-wide'} ({p.country}); radius {p.radius_km} km; "
        f"up to {p.max_days_old} days old; target {p.target_postings} Postings; category {p.category or 'none'}"
    )


def _item(label: str, lines: list[str], empty: str) -> str:
    if not lines:
        return f"- **{label}:** {empty}"
    if len(lines) == 1:
        return f"- **{label}:** {lines[0]}"
    return "\n".join([f"- **{label}:**", *(f"  - {line}" for line in lines)])


def _run_notes(brief: MarketBrief, postings: list[Posting]) -> str:
    notes = brief.run_notes
    by_source = ", ".join(f"{SOURCE_NAMES[s]} {n}" for s, n in sorted(Counter(p.source for p in postings).items()))
    analysed = f"{notes.postings_analysed.count}" + (f" ({by_source})" if by_source else "")
    items = [
        _item("Questions", [f"{q.text} → {q.answer or 'no answer'}" for q in notes.questions], "None asked"),
        _item("Assumptions", [f"{a.about}: {a.value} ({a.reason})" for a in notes.assumptions], "None"),
        f"- **Focus:** {', '.join(notes.focus) or 'All Dimensions'}",
        f"- **Final search plan:** {_plan(notes.final_plan)}",
    ]
    if notes.earlier_plans:
        items.append(_item("Earlier search plans", [_plan(p) for p in notes.earlier_plans], ""))
    items += [
        f"- **Postings analysed:** {analysed}",
        _item("Source match counts", notes.match_totals, "None"),
        _item("Caveats", notes.caveats, "None"),
    ]
    if notes.attribution:
        items.append(f"- {notes.attribution}")
    return "## Run Notes\n\n" + "\n".join(items)


def render_markdown(brief: MarketBrief, postings: list[Posting]) -> str:
    if brief.insights or postings or any(brief.recommendations.model_dump().values()):
        raise NotImplementedError("Markdown for a Brief with Postings is not built yet")

    request, outlook = brief.hiring_request, brief.outlook
    summary = brief.summary
    target = brief.run_notes.final_plan.target_postings
    if brief.stats.sample_size < target:
        summary += f"\n\nWeak Sample: {brief.stats.sample_size} Postings against a target of {target}. Treat this Brief as directional."

    parts = [f"> {REPLAY_BANNER}"] if brief.replayed else []
    parts += [
        f"# Market Brief: {request.role}, {request.location}",
        f"## Summary\n\n{summary}",
        f"## Hiring Outlook\n\n**{outlook.rating.value.replace('_', ' ').capitalize()}**\n\n{outlook.reason}",
        "## Client Recommendations\n\n" + "\n".join(f"- {line}" for line in NO_RECOMMENDATIONS),
        "## Insights\n\nNone: this Brief has no findings.",
        _run_notes(brief, postings),
        "## Evidence\n\nNone.",
        "## Postings analysed\n\nNone.",
    ]
    return "\n\n".join(parts) + "\n"
