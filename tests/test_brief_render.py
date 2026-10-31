import asyncio

from talent_scout.analysis.stats import compute_stats
from talent_scout.brief.nodes import make_nodes
from talent_scout.collection.testing import FETCHED_AT, posting, record, state_with
from talent_scout.kernel.testing import make_settings
from talent_scout.runtime.testing import fake_deps


def sample_state(n=12, edits=None):
    postings = [posting(str(i), company=f"Company {i}") for i in range(n)]
    for i, changes in (edits or {}).items():
        postings[i] = postings[i].model_copy(update=changes)
    state = state_with(
        postings={p.key: p for p in postings}, sample=[p.key for p in postings], fetches=[record([], fetched_at=FETCHED_AT)]
    )
    return state.model_copy(update={"stats": compute_stats(state)[0]})


def run(state) -> dict:
    nodes = make_nodes(fake_deps(make_settings()))

    async def go():
        update = await nodes["write_brief"](state)
        return await nodes["render"](state.model_copy(update=update))

    return asyncio.run(go())


def test_a_run_with_postings_gets_tagged_insights_from_the_rule_draft():
    update = run(sample_state())
    brief, md = update["brief"], update["brief_markdown"]

    assert brief.summary.startswith("The Sample holds 12 Postings")
    assert {i.dimension for i in brief.insights} == {"demand", "compensation", "competition", "titles_seniority"}
    assert all(i.confidence_reason.startswith(i.confidence.value.capitalize()) for i in brief.insights)
    assert "**[Medium]** Postings in the Sample\n" in md
    assert "Medium: weakest cited Stat has 12 Postings from 12 employers" in md
    assert "High: 30+ Postings from 10+ employers." in md  # the key
    assert "Weak Sample: 12 Postings against a target of 20" in md


def test_identical_postings_share_one_reference_and_the_evidence_list_and_table_follow():
    md = run(sample_state())["brief_markdown"]

    # The sample size, the pay share, the top title and the title recommendation cover every Posting, the top employer only one.
    assert md.count("Evidence: 12 Postings [E1]") == 4
    assert "Evidence: 1 Posting [E2]" in md
    evidence = md.split("## Evidence")[1].split("## Postings analysed")[0]
    assert evidence.count("- **E") == 2 and "adzuna:0, adzuna:1" in evidence
    table = md.split("## Postings analysed")[1]
    assert table.count("\n| adzuna:") == 12 and "[link](<https://example.com/0>)" in table


def test_posting_text_cannot_break_the_table_and_only_http_links_appear():
    md = run(sample_state(edits={0: {"title": "Data | Analyst\nSenior", "url": "javascript:alert(1)"}, 1: {"url": "ftp://x/y"}}))["brief_markdown"]
    table = md.split("## Postings analysed")[1]

    assert "| adzuna:0 | Data Analyst Senior | Company 0 |  |" in table
    assert "javascript" not in table and "ftp:" not in table


def test_the_outlook_only_says_too_few_postings_when_it_is_true():
    assert "Only 12 Postings, too few" in run(sample_state(12))["brief"].outlook.reason
    rated = run(sample_state(25))["brief"].outlook
    # The fixture's request is senior and its Postings are all recent, so 25 employers with a high bar is Hard to fill.
    assert rated.rating == "hard_to_fill" and rated.stat_ids == ["competition.distinct_employers", "demand.trend"]
    assert rated.reason.startswith("25 employers across 25 Postings, with a senior level requested, a rising trend.")


def test_the_title_name_split_matches_a_real_analysis_label():
    # A title holding ": " is the case a split on the first one would get wrong.
    state = sample_state(edits={i: {"title": "Data Analyst: Contract"} for i in range(12)})
    assert run(state)["brief"].recommendations.job_title.title == "Data Analyst: Contract"


def test_the_markdown_shows_the_recommendations_with_their_reasons_and_evidence():
    md = run(sample_state())["brief_markdown"]
    assert "- **Job title:** Data Analyst. Used in 12 Postings from 12 employers. Evidence: 12 Postings [E1]" in md
    assert "Not enough evidence to suggest a salary band." in md and "Not enough evidence to suggest top skills." in md


def test_two_renders_give_identical_bytes():
    state = sample_state()
    assert run(state)["brief_markdown"] == run(state)["brief_markdown"]
