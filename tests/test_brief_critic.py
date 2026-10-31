import asyncio
import dataclasses

import httpx
import pytest

from talent_scout.brief.nodes import MAX_REVISIONS, after_critic, make_nodes
from talent_scout.brief.prompts import CRITIC_NOUL
from talent_scout.brief.types import BriefDraft, InsightDraft, InsightVerdict
from talent_scout.kernel import llm
from talent_scout.kernel.jev import Jev
from talent_scout.kernel.llm import LLMExhausted, Tiers
from talent_scout.kernel.state import LogKind, RunLogEntry, State
from talent_scout.kernel.testing import fake_classifier, make_settings
from talent_scout.kernel.thresholds import CUTS
from talent_scout.runtime.testing import fake_deps
from test_brief_render import sample_state
from test_brief_writer import REQUEST, model, stats

SAMPLE = InsightDraft(text="Sample size: 125 Postings", stat_ids=["demand.sample_size"])
TREND = InsightDraft(text="Trend: rising", stat_ids=["demand.trend"])
PAY = InsightDraft(text="Advertised pay median: $134,000", stat_ids=["comp.advertised.median"])
YES, NO = InsightVerdict(supported=True, p_yes=0.9), InsightVerdict(supported=False, p_yes=0.1)


def state(insights, verdicts=(), **fields) -> State:
    draft = BriefDraft(summary="The Sample holds 125 Postings.", summary_stat_ids=["demand.sample_size"], insights=list(insights))
    return State(request_text="x", hiring_request=REQUEST, stats=stats(), brief_draft=draft, critic_verdicts=list(verdicts), **fields)


def nodes(*models, answers=None, classifier=None):
    deps = fake_deps(make_settings())
    jev = Jev(classifier or fake_classifier(answers or {}), CUTS)
    return make_nodes(dataclasses.replace(deps, jev=jev, tiers=Tiers({"cheap": list(models), "strong": list(models)}, deps.settings)))


def run(node, st, **kw):
    return asyncio.run(nodes(**kw)[node](st))


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    monkeypatch.setattr(llm, "_BACKOFF", False)


def test_only_fresh_insights_are_judged_and_the_claim_carries_just_the_cited_stats():
    classifier = fake_classifier({"supported": 0.9})
    update = run("critic", state([SAMPLE, TREND, PAY], [YES]), classifier=classifier)

    assert [v.supported for v in update["critic_verdicts"]] == [True, True, True] and len(classifier.calls) == 2
    sent = classifier.calls[0]
    assert sent["questions"] == {"supported": CRITIC_NOUL}
    assert sent["state"]["claim"] == "Trend: rising"
    assert sent["state"]["stats"] == [{"id": "demand.trend", "label": "Trend: rising", "value": "rising", "unit": None}]
    assert sent["state"]["hiring_request"]["role"] == "Data Engineer"
    assert classifier.calls[1]["state"]["stats"][0]["value"] == "134,000"  # formatted, not 134000.0


def test_nothing_to_judge_makes_no_call_and_routes_to_render():
    classifier = fake_classifier({"supported": 0.9})
    update = run("critic", state([]), classifier=classifier)

    assert classifier.calls == [] and update["critic_verdicts"] == []
    assert update["run_log"][-1].data["outcome"] == "render"


def test_the_route_entry_has_each_score_and_the_outcome():
    flagged = run("critic", state([SAMPLE, TREND]), answers={"supported": 0.2})
    entry = flagged["run_log"][-1]
    assert entry.kind == LogKind.route and entry.data == {"scores": [0.2, 0.2], "outcome": "write_brief"}
    assert [v.supported for v in flagged["critic_verdicts"]] == [False, False]

    passed = run("critic", state([SAMPLE]), answers={"supported": 0.8})["run_log"][-1]
    assert passed.data == {"scores": [0.8], "outcome": "render"}


@pytest.mark.parametrize("verdicts, revisions, route", [
    ([YES, YES], 0, "render"),
    ([YES, NO], 0, "write_brief"),
    ([YES, NO], 1, "write_brief"),
    ([YES, NO], MAX_REVISIONS, "render"),
])
def test_after_critic_routes(verdicts, revisions, route):
    assert after_critic(state([SAMPLE, TREND], verdicts, revisions=revisions)) == route


def test_the_degraded_caveat_fires_once_per_pass_with_its_count_and_not_on_a_normal_pass():
    plain = run("critic", state([SAMPLE, TREND]), answers={"supported": 0.9})
    assert not [e for e in plain["run_log"] if e.kind == LogKind.caveat]

    # A caveat past Jev's size limit shortens both requests.
    long = RunLogEntry(node="stats", kind=LogKind.caveat, message="x" * 40_000, data={})
    update = run("critic", state([SAMPLE, TREND], run_log=[long]), answers={"supported": 0.9})
    degraded = [e for e in update["run_log"] if e.message.startswith("Critic degraded")]
    assert len(degraded) == 1 and degraded[0].kind == LogKind.caveat and "2 Insights" in degraded[0].message


def test_a_revision_keeps_supported_insights_byte_identical_and_replaces_only_the_flagged():
    st = state([SAMPLE, TREND, PAY], [YES, NO, YES], revisions=0)
    m = model('{"insights": [{"text": "The trend is rising", "stat_ids": ["demand.trend"]}]}')
    update = asyncio.run(nodes(m)["write_brief"](st))

    texts = [i.text for i in update["brief_draft"].insights]
    assert texts == [SAMPLE.text, PAY.text, "The trend is rising"]
    assert update["brief_draft"].insights[0] is st.brief_draft.insights[0]
    assert update["critic_verdicts"] == [YES, YES] and update["revisions"] == 1
    # The reviser sees the flagged Insight and its ids, not the kept ones.
    sent = m.seen[0][-1].content
    assert "Flagged Insights" in sent and "- Trend: rising | demand.trend" in sent and "- Sample size: 125 Postings |" not in sent
    assert update["run_log"][-1].data["draft"] == "revision"


def test_a_reply_with_no_replacements_drops_the_flagged_claims():
    st = state([SAMPLE, TREND], [YES, NO])
    update = asyncio.run(nodes(model('{"insights": []}'))["write_brief"](st))

    assert update["brief_draft"].insights == [SAMPLE] and update["critic_verdicts"] == [YES]
    assert after_critic(st.model_copy(update=update)) == "render"


def test_replacements_cannot_push_the_brief_over_its_cap():
    st = state([SAMPLE, TREND, PAY], [YES, YES, NO])  # 125 Postings, cap 8, so 6 left
    too_many = '{"insights": [' + ",".join(['{"text": "Trend: rising", "stat_ids": ["demand.trend"]}'] * 7) + "]}"
    m = model(too_many, '{"insights": []}')
    update = asyncio.run(nodes(m)["write_brief"](st))

    assert "over the maximum of 6" in m.seen[1][-1].content and update["revisions"] == 1


def test_bad_output_during_a_revision_stops_the_loop_with_the_draft_standing():
    st = state([SAMPLE, TREND], [YES, NO])
    update = asyncio.run(nodes(model("bad", "worse"))["write_brief"](st))

    assert update == {"revisions": MAX_REVISIONS}
    assert after_critic(st.model_copy(update=update)) == "render"


def test_a_transient_failure_during_a_revision_propagates():
    boom = httpx.ConnectError("down")
    with pytest.raises(LLMExhausted) as e:
        asyncio.run(nodes(model(boom, boom, boom))["write_brief"](state([SAMPLE, TREND], [YES, NO])))
    assert not e.value.bad_output


def rendered(verdicts):
    market = sample_state()
    drafts = [InsightDraft(text="Sample size", stat_ids=["demand.sample_size"]), InsightDraft(text="Employers", stat_ids=["competition.distinct_employers"])]
    draft = BriefDraft(summary="The Sample holds 12 Postings.", summary_stat_ids=["demand.sample_size"], insights=drafts)
    return asyncio.run(nodes()["render"](market.model_copy(update={"brief_draft": draft, "critic_verdicts": verdicts})))


def test_an_unsupported_insight_ships_capped_at_medium_with_the_caveat_in_the_run_notes():
    update = rendered([YES, NO])
    brief = update["brief"]

    assert brief.run_notes.caveats[-1].startswith("Insights not confirmed: 1 ")
    assert "the critic couldn't confirm it" in brief.insights[1].confidence_reason
    assert "the critic couldn't confirm it" not in brief.insights[0].confidence_reason
    assert "Insights not confirmed" in update["brief_markdown"]


def test_all_supported_ships_without_the_caveat():
    brief = rendered([YES, YES])["brief"]
    assert not any(c.startswith("Insights not confirmed") for c in brief.run_notes.caveats)
