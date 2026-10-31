from collections import Counter
from urllib.parse import quote, urlparse

from talent_scout.brief.rules import SOURCE_NAMES
from talent_scout.brief.types import ClientRecommendations, HiringOutlook, Insight, MarketBrief
from talent_scout.kernel.text import plural
from talent_scout.kernel.types import Evidence, Posting, SearchPlan

REPLAY_BANNER = "Replayed run: jobs data, LLM and Jev responses came from the replay cache, not live sources"
NO_RECOMMENDATIONS = (
    "Not enough evidence to suggest a job title.",
    "Not enough evidence to suggest a salary band.",
    "Not enough evidence to suggest top skills.",
)
CONFIDENCE_KEY = (
    "High: 30+ Postings from 10+ employers. Medium: 10+ from 5+, or capped because pay is estimated, skills come from snippets, "
    "data is old or the critic couldn't confirm it. Low: anything thinner, directional only. An Insight takes its weakest cited figure."
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


def _evidence(refs: dict[tuple[str, ...], int]) -> str:
    if not refs:
        return "## Evidence\n\nNone."
    return "## Evidence\n\n" + "\n".join(f"- **E{n}:** {', '.join(keys)}" for keys, n in refs.items())


def _postings_table(postings: list[Posting]) -> str:
    if not postings:
        return "## Postings analysed\n\nNone."
    rows = [f"| {_cell(p.key)} | {_cell(p.title)} | {_cell(p.company or '')} | {_link(p.url)} |" for p in postings]
    return "\n".join(["## Postings analysed", "", "| Key | Title | Company | Link |", "|---|---|---|---|", *rows])


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


def _cell(text: str) -> str:
    # Posting text comes from outside, so it can't be allowed to end a cell or a row.
    return " ".join(text.replace("|", " ").split())


def _link(url: str) -> str:
    # Only http(s): anything else, such as javascript:, would be a live link in the reader's viewer.
    if urlparse(url).scheme not in ("http", "https"):
        return ""
    return f"[link](<{quote(url, safe=':/?#[]@!$&()*+,;=%~-._')}>)"


def _evidence_line(evidence: Evidence, refs: dict[tuple[str, ...], int]) -> str:
    n = refs.setdefault(tuple(evidence.posting_keys), len(refs) + 1)
    return f"Evidence: {plural(evidence.count, 'Posting')} [E{n}]"


def _outlook(outlook: HiringOutlook, refs: dict[tuple[str, ...], int]) -> str:
    text = f"## Hiring Outlook\n\n**{outlook.rating.value.replace('_', ' ').capitalize()}**\n\n{outlook.reason}"
    # The default rests on no Stats, so it has no Evidence to show.
    return f"{text} {_evidence_line(outlook.evidence, refs)}" if outlook.stat_ids else text


def _recommendations(recs: ClientRecommendations, refs: dict[tuple[str, ...], int]) -> str:
    band = recs.salary_band
    shown = (
        ("Job title", recs.job_title and recs.job_title.title),
        ("Salary band", band and f"{band.low:,.0f} to {band.high:,.0f} {band.unit}"),
        ("Top skills", recs.top_skills and ", ".join(recs.top_skills.skills)),
    )
    lines = []
    for (label, value), rec, missing in zip(shown, (recs.job_title, band, recs.top_skills), NO_RECOMMENDATIONS):
        lines.append(f"- **{label}:** {value}. {rec.reason} {_evidence_line(rec.evidence, refs)}" if rec else f"- {missing}")
    return "## Client Recommendations\n\n" + "\n".join(lines)


def _insights(insights: list[Insight], refs: dict[tuple[str, ...], int]) -> str:
    if not insights:
        return "## Insights\n\nNone: this Brief has no findings."
    items = [f"**[{i.confidence.value.capitalize()}]** {i.text}\n\n{i.confidence_reason}. {_evidence_line(i.evidence, refs)}" for i in insights]
    return "## Insights\n\n" + "\n\n".join(items) + "\n\n" + CONFIDENCE_KEY


def render_markdown(brief: MarketBrief, postings: list[Posting]) -> str:
    request = brief.hiring_request
    summary = brief.summary
    target = brief.run_notes.final_plan.target_postings
    if brief.stats.sample_size < target:
        summary += f"\n\nWeak Sample: {brief.stats.sample_size} Postings against a target of {target}. Treat this Brief as directional."

    parts = [f"> {REPLAY_BANNER}"] if brief.replayed else []
    refs: dict[tuple[str, ...], int] = {}  # Posting keys -> E number, by first appearance, so these run in page order
    parts += [
        f"# Market Brief: {request.role}, {request.location}",
        f"## Summary\n\n{summary}",
        _outlook(brief.outlook, refs),
        _recommendations(brief.recommendations, refs),
        _insights(brief.insights, refs),
        _run_notes(brief, postings),
        _evidence(refs),
        _postings_table(postings),
    ]
    return "\n\n".join(parts) + "\n"
