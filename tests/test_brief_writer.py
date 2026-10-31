import asyncio
import dataclasses
import json

import httpx
import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field, ValidationError

from talent_scout.brief.nodes import MAX_REVISIONS, make_nodes
from talent_scout.brief.rules import checked_draft, rule_draft
from talent_scout.brief.types import BriefDraft
from talent_scout.kernel import llm
from talent_scout.kernel.llm import LLMExhausted, Tiers
from talent_scout.kernel.state import LogKind, RunLogEntry, State
from talent_scout.kernel.testing import FakeToolChatModel, make_settings
from talent_scout.kernel.types import Dimension, Evidence, HiringRequest, MarketStats, Stat
from talent_scout.runtime.testing import fake_deps

REQUEST = HiringRequest(
    role="Data Engineer", location="Austin", country="us", seniority=None, employment_type=None,
    work_mode=None, currency=None, purpose=None,
)
CAVEAT = "Fewer than 5 advertised salaries, so no advertised pay is reported"


def stat(id, dimension, label, value, unit=None) -> Stat:
    return Stat(id=id, dimension=dimension, label=label, value=value, unit=unit, evidence=Evidence(posting_keys=[]))


def stats(size=125) -> MarketStats:
    return MarketStats(sample_size=size, stats=[
        stat("demand.sample_size", Dimension.demand, f"Sample size: {size} Postings", float(size), "postings"),
        stat("demand.trend", Dimension.demand, "Trend: rising", "rising"),
        stat("competition.distinct_employers", Dimension.competition, "61 distinct employers", 61.0, "employers"),
        stat("competition.direct_share", Dimension.competition, "Direct employers: 38.4% of extracted Postings", 38.4, "%"),
        stat("comp.advertised.median", Dimension.compensation, "Advertised pay median: $134,000", 134000.0, "USD/year"),
        stat("skills.s3.count", Dimension.skills, "S3: 7 of 90 extracted Postings", 7.0, "postings"),
    ])


def reply(summary="The Sample holds 125 Postings.", ids=("demand.sample_size",), insights=None) -> str:
    insights = insights if insights is not None else [{"text": "Sample size: 125 Postings", "stat_ids": ["demand.sample_size"]}]
    return json.dumps({"summary": summary, "summary_stat_ids": list(ids), "insights": insights})


def validate(text: str, cap=8) -> BriefDraft:
    return checked_draft(stats(), f"{REQUEST.role} {REQUEST.location} {CAVEAT}", cap).model_validate_json(text)


def insight(text, *ids) -> dict:
    return {"text": text, "stat_ids": list(ids)}


@pytest.mark.parametrize("bad, complaint", [
    (reply(ids=("demand.nope",)), "unknown Stat ids: demand.nope"),
    (reply(insights=[insight("Fine.", "no.such.stat")]), "Insight 1 cites unknown Stat ids"),
    (reply(summary="  "), "Summary is blank"),
    (reply(insights=[insight(" ", "demand.sample_size")]), "Insight 1 is blank"),
    (reply(ids=()), "Summary cites no Stat ids"),
    (reply(insights=[insight("Fine.")]), "Insight 1 cites no Stat ids"),
    (reply(insights=[]), "no Insights"),
    (reply(insights=[insight("Fine.", "demand.sample_size")] * 3), "3 Insights, over the maximum of 2"),
    (reply(insights=[insight("There are 99 Postings", "demand.sample_size")]), "figures found in no Stat, Caveat or the request: 99"),
])
def test_the_check_rejects(bad, complaint):
    with pytest.raises(ValidationError, match=complaint):
        validate(bad, cap=2)


@pytest.mark.parametrize("text", [
    "S3 appears in 7 of 90 extracted Postings",  # S3 is a name, not a number
    "Pay is around $134k",  # checked as 134,000
    "About 38% hire directly",  # 38.4 rounded
    "Trend is rising and 61 employers post",
    "Austin has 5 advertised salaries at most",  # Caveat and request figures count
])
def test_the_check_passes_figures_in_a_stat_caveat_or_request(text):
    validate(reply(insights=[insight(text, "demand.sample_size")]))


def test_a_figure_from_a_stat_it_did_not_cite_passes_for_the_critic_to_flag():
    validate(reply(insights=[insight("There are 61 employers", "demand.sample_size")]))


def test_rule_draft_passes_its_own_checks():
    market = stats()
    checked_draft(market, "", 8).model_validate(rule_draft(market).model_dump())


class Scripted(FakeToolChatModel):
    """Replays replies in order, raising any Exception item, and keeps every prompt it was sent."""

    script: list = Field(default_factory=list)
    seen: list = Field(default_factory=list)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(messages)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return ChatResult(generations=[ChatGeneration(message=item if isinstance(item, AIMessage) else AIMessage(content=item))])


def write(*models, market=None, **fields) -> dict:
    deps = fake_deps(make_settings())
    deps = dataclasses.replace(deps, tiers=Tiers({"cheap": list(models), "strong": list(models)}, deps.settings))
    state = State(request_text="x", hiring_request=REQUEST, stats=market or stats(), **fields)
    return asyncio.run(make_nodes(deps)["write_brief"](state))


def model(*script) -> Scripted:
    return Scripted(messages=iter([]), script=list(script))


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    monkeypatch.setattr(llm, "_BACKOFF", False)


def test_a_bad_reply_passes_on_the_feedback_retry_and_the_stored_draft_is_a_plain_brief_draft():
    m = model(reply(insights=[insight("There are 99 Postings", "demand.sample_size")]), reply())
    update = write(m)

    assert len(m.seen) == 2 and "figures found in no Stat" in m.seen[1][-1].content
    assert type(update["brief_draft"]) is BriefDraft
    assert update["brief_draft"].insights[0].text == "Sample size: 125 Postings"
    assert "revisions" not in update


def test_bad_output_from_every_model_including_a_runaway_gives_the_rule_draft_and_spends_the_revisions():
    runaway = AIMessage(content='{"summary": "' + " " * 50, response_metadata={"finish_reason": "length"})
    update = write(model(runaway), model("bad", "worse"))

    market = stats()
    assert update["brief_draft"] == rule_draft(market)
    assert update["revisions"] == MAX_REVISIONS
    entry = update["run_log"][-1]
    assert entry.kind == LogKind.caveat and entry.message.startswith("Brief written by rule")


def test_a_transient_failure_on_every_model_propagates():
    boom = httpx.ConnectError("down")
    with pytest.raises(LLMExhausted) as e:
        write(model(boom, boom, boom))
    assert not e.value.bad_output


def test_the_writer_gets_its_input_in_order_with_formatted_values_and_the_default_outlook_hidden():
    caveat = RunLogEntry(node="stats", kind=LogKind.caveat, message=CAVEAT, data={})
    m = model(reply())
    write(m, run_log=[caveat], focus=[Dimension.skills, Dimension.demand])
    text = m.seen[0][1].content
    lines = text.splitlines()

    assert json.loads(lines[0])["role"] == "Data Engineer"
    assert lines[1:6] == ["Focus: skills, demand", "Maximum Insights: 8", "Outlook: competitive", "Caveats:", f"- {CAVEAT}"]
    assert lines[6] == "Stats (id | label | value | unit):"
    assert lines[7] == "demand.sample_size | Sample size: 125 Postings | 125 | postings"
    assert "comp.advertised.median | Advertised pay median: $134,000 | 134,000 | USD/year" in lines
    assert "demand.trend | Trend: rising | rising | " in lines
    assert ".0" not in text.replace("38.4", "")

    thin = model(reply("The Sample holds 8 Postings.", insights=[insight("Sample size: 8 Postings", "demand.sample_size")]))
    write(thin, market=stats(8))
    assert "Outlook: not rated" in thin.seen[0][1].content and "Maximum Insights: 3" in thin.seen[0][1].content
