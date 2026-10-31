import asyncio
import json
import re
from dataclasses import replace

import httpx
import pytest
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import Field

from talent_scout.analysis.nodes import (
    MAX_BATCH_CHARS,
    MAX_BATCH_POSTINGS,
    _batches,
    _grounded,
    fan_out,
    make_nodes,
)
from talent_scout.analysis.stats import fold, mentions
from talent_scout.analysis.types import (
    EmployerType,
    ExtractBatch,
    PostingFacts,
    Requirement,
    Seniority,
    SkillMention,
)
from talent_scout.collection.testing import make_deps, posting, state_with
from talent_scout.kernel import llm
from talent_scout.kernel.llm import LLMExhausted, Tiers
from talent_scout.kernel.state import State
from talent_scout.kernel.testing import FakeToolChatModel
from talent_scout.kernel.types import Source


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    monkeypatch.setattr(llm, "_BACKOFF", False)


def facts(ref: int, *skills: str, years: int | None = None, seniority="mid", employer="direct") -> dict:
    return {
        "ref": ref, "skills": [{"name": s, "requirement": "unstated"} for s in skills],
        "seniority": seniority, "years_min": years, "employer_type": employer,
    }


def reply(*items: dict) -> str:
    return json.dumps({"items": list(items)})


def post(id: str, description: str = "Python and SQL", **kw):
    return posting(id, description=description, **kw)


def run_extract(deps, *postings):
    return asyncio.run(make_nodes(deps)["batch_extract"](ExtractBatch(postings=list(postings))))


# _batches and fan_out


def test_900_adzuna_sized_postings_make_45_batches():
    batches = _batches([post(f"{i:03}", "x" * 500) for i in range(900)])
    assert len(batches) == 45 and {len(b) for b in batches} == {MAX_BATCH_POSTINGS}


def test_the_count_limit_splits_short_postings():
    batches = _batches([post(f"{i:02}", "short") for i in range(MAX_BATCH_POSTINGS + 1)])
    assert [len(b) for b in batches] == [MAX_BATCH_POSTINGS, 1]


def test_the_character_limit_splits_usajobs_sized_postings():
    # 3,500 characters each: five fit under 20,000, a sixth would not.
    batches = _batches([post(f"{i:02}", "x" * 3500, source=Source.usajobs) for i in range(12)])
    assert [len(b) for b in batches] == [5, 5, 2]
    assert all(sum(len(p.description) for p in b) <= MAX_BATCH_CHARS for b in batches)


def test_one_oversized_posting_gets_a_batch_of_its_own():
    big = post("1", "x" * (MAX_BATCH_CHARS + 1))
    batches = _batches([post("0"), big, post("2")])
    assert [[p.source_id for p in b] for b in batches] == [["0"], ["1"], ["2"]]


def test_batches_are_the_same_whatever_the_input_order():
    postings = [post(f"{i:02}", "x" * 3500) for i in range(12)]
    assert _batches(postings) == _batches(postings[::-1])


def test_fan_out_sends_one_batch_each_and_an_empty_sample_goes_to_stats():
    assert fan_out(state_with()) == "stats"
    postings = [post(f"{i:02}") for i in range(25)]
    sends = fan_out(state_with(postings={p.key: p for p in postings}, sample=[p.key for p in postings]))
    assert [s.node for s in sends] == ["batch_extract"] * 2
    assert [len(s.arg.postings) for s in sends] == [20, 5]


# grounding


def mention(name: str) -> SkillMention:
    return SkillMention(name=name, requirement=Requirement.unstated)


def ground(skills: list[str], text: str, years: int | None = None, title: str = "Engineer"):
    item = PostingFacts(
        ref=0, skills=[mention(s) for s in skills], seniority=Seniority.mid, years_min=years,
        employer_type=EmployerType.direct,
    )
    return _grounded(item, post("1", text, title=title))


def test_c_is_not_grounded_by_cpp_and_r_is_not_found_inside_a_word():
    assert not mentions(fold("C"), fold("We use C++ and C#"))
    assert mentions(fold("C++"), fold("We use C++ and C#"))
    assert not mentions(fold("R"), fold("Strong reporting skills"))
    assert mentions(fold("R"), fold("Experience with R, Python"))


def test_an_invented_skill_is_dropped_and_counted_but_case_and_title_still_match():
    out = ground(["python", "Kubernetes", "Welder"], "We need PYTHON.", title="Welder")
    assert [s.name for s in out.skills] == ["python", "Welder"]
    assert out.ungrounded == 1


def test_a_name_that_folds_to_nothing_is_never_grounded():
    assert ground(["..."], "Python").skills == []


@pytest.mark.parametrize(
    ("years", "text", "expected"),
    [(5, "Needs 5+ years of SQL", 5), (5, "Needs five years", None), (5, "Needs 15 years", None), (41, "Needs 41 years", None)],
)
def test_years_min_must_be_in_the_text_and_at_most_40(years, text, expected):
    assert ground([], text, years).years_min == expected


# batch_extract


def test_refs_map_to_keys_and_a_repeat_or_out_of_range_ref_is_ignored():
    a, b, c = post("a", "Python"), post("b", "Java here"), post("c", "Nothing")
    deps, cheap, *_ = make_deps(cheap=[reply(
        facts(1, "Java"), facts(0, "Python", seniority="senior"), facts(0, "Java"), facts(7, "Python"), facts(-1, "Python"),
    )])

    update = run_extract(deps, a, b, c)

    found = update["extractions"]
    # c has no answer so it has no Extraction, and the first answer for a wins.
    assert set(found) == {a.key, b.key}
    assert [s.name for s in found[a.key].skills] == ["Python"] and found[a.key].seniority == Seniority.senior
    assert [s.name for s in found[b.key].skills] == ["Java"]
    # One block per Posting with its position as ref, and nothing about the Hiring Request.
    assert cheap.seen[0][1].content == (
        "ref 0\ntitle: Data Analyst\ncompany: Company a\ndescription: Python\n\n"
        "ref 1\ntitle: Data Analyst\ncompany: Company b\ndescription: Java here\n\n"
        "ref 2\ntitle: Data Analyst\ncompany: Company c\ndescription: Nothing"
    )


def test_bad_output_returns_nothing_and_a_transient_failure_raises():
    deps, *_ = make_deps(cheap=["bad", "bad"])
    assert run_extract(deps, post("a")) == {}

    deps, *_ = make_deps(cheap=[httpx.ConnectError("down")] * 3)
    with pytest.raises(LLMExhausted):
        run_extract(deps, post("a"))


# resume


class Flaky(FakeToolChatModel):
    """Answers every ref with Python, except that the batch holding 'Job 24' fails while `down` is set."""

    down: bool = True
    seen: list = Field(default_factory=list)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        text = messages[-1].content
        self.seen.append(text)
        if self.down and "Job 24" in text:
            raise httpx.ConnectError("down")
        refs = [int(r) for r in re.findall(r"^ref (\d+)$", text, re.M)]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=reply(*(facts(r, "Python") for r in refs))))])


def test_resume_reruns_only_the_failed_batch_and_normalise_skills_runs_once():
    flaky = Flaky(messages=iter([]))
    deps, *_ = make_deps()
    deps = replace(deps, tiers=Tiers({"cheap": [flaky], "strong": [flaky]}, deps.settings))
    visits = []

    def stage(name):
        async def node(state: State) -> dict:
            visits.append(name)
            return {}

        return node

    builder = StateGraph(State)
    builder.add_node("batch_extract", make_nodes(deps)["batch_extract"])
    builder.add_node("normalise_skills", stage("normalise_skills"))
    builder.add_node("stats", stage("stats"))
    builder.add_edge("batch_extract", "normalise_skills")
    builder.add_edge("normalise_skills", "stats")
    builder.add_edge("stats", END)
    builder.add_conditional_edges(START, fan_out, ["batch_extract", "stats"])
    graph = builder.compile(checkpointer=InMemorySaver())

    postings = [post(f"{i:02}", title=f"Job {i}") for i in range(25)]
    start = state_with(postings={p.key: p for p in postings}, sample=[p.key for p in postings]).model_dump()
    config = {"configurable": {"thread_id": "t"}}

    with pytest.raises(LLMExhausted):
        asyncio.run(graph.ainvoke(start, config))
    assert visits == []
    first_batch_calls = sum("Job 24" not in t for t in flaky.seen)

    flaky.down = False
    final = asyncio.run(graph.ainvoke(None, config))

    assert len(final["extractions"]) == 25
    assert sum("Job 24" not in t for t in flaky.seen) == first_batch_calls == 1
    assert visits == ["normalise_skills", "stats"]
