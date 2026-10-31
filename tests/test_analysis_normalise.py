import asyncio
import json

import httpx
import pytest

from talent_scout.analysis.nodes import MAX_SKILLS_TO_MERGE, make_nodes
from talent_scout.analysis.types import EmployerType, Extraction, Requirement, Seniority, SkillMention
from talent_scout.collection.testing import make_deps, state_with
from talent_scout.kernel import llm
from talent_scout.kernel.llm import LLMExhausted
from talent_scout.kernel.state import LogKind


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    monkeypatch.setattr(llm, "_BACKOFF", False)


def extraction(*skills: str) -> Extraction:
    return Extraction(
        skills=[SkillMention(name=s, requirement=Requirement.unstated) for s in skills],
        seniority=Seniority.mid, years_min=None, employer_type=EmployerType.direct, ungrounded=0,
    )


def groups(*gs: tuple[str, list[str]]) -> str:
    return json.dumps({"groups": [{"canonical": c, "variants": v} for c, v in gs]})


def run_normalise(deps, **extractions: Extraction):
    state = state_with(extractions=extractions)
    return asyncio.run(make_nodes(deps)["normalise_skills"](state))


def test_no_names_means_no_call_and_an_empty_alias_map_with_a_log_entry():
    deps, cheap, *_ = make_deps()

    update = run_normalise(deps, a=extraction())

    assert update["skill_aliases"] == {}
    assert update["run_log"][-1].node == "normalise_skills"
    assert cheap.seen == []


def test_a_variant_not_in_the_input_is_ignored_and_the_first_group_wins():
    deps, cheap, *_ = make_deps(cheap=[groups(
        ("Apache Spark", ["spark", "pyspark", "Apache Spark"]),
        ("Spark SQL", ["spark", "sql"]),
    )])

    update = run_normalise(deps, a=extraction("Spark", "Apache Spark"), b=extraction("Spark", "SQL"))

    # pyspark never appeared, spark stays with the first group, and a variant equal to its canonical is skipped.
    assert update["skill_aliases"] == {"spark": "Apache Spark", "sql": "Spark SQL"}
    # Folded, deduplicated and sorted, so the prompt is the same on replay.
    assert cheap.seen[0][1].content == "apache spark\nspark\nsql"


def test_only_the_most_common_names_are_sent():
    deps, cheap, *_ = make_deps(cheap=[groups()])
    names = [f"skill {i:03}" for i in range(MAX_SKILLS_TO_MERGE + 1)]

    run_normalise(deps, a=extraction(*names), b=extraction(*names[1:]))

    # The one name seen once is the one that gets cut.
    sent = cheap.seen[0][1].content.splitlines()
    assert len(sent) == MAX_SKILLS_TO_MERGE and "skill 000" not in sent


def test_reciprocal_and_chained_groups_resolve_to_one_name():
    deps, *_ = make_deps(cheap=[groups(
        ("analytics", ["data analytics", "analytics"]),
        ("data analytics", ["analytics", "data analytics"]),
        ("beta", ["alpha", "beta"]),
        ("gamma", ["beta", "gamma"]),
    )])

    update = run_normalise(deps, a=extraction("Data Analytics", "Analytics", "Alpha", "Beta", "Gamma"))

    assert update["skill_aliases"] == {"data analytics": "analytics", "alpha": "gamma", "beta": "gamma"}


def test_the_merge_note_lists_every_merge():
    deps, *_ = make_deps(cheap=[groups(("Apache Spark", ["spark", "apache spark"]), ("PostgreSQL", ["postgres"]))])

    update = run_normalise(deps, a=extraction("Spark", "Apache Spark", "Postgres"))

    entry = update["run_log"][-1]
    assert entry.kind == LogKind.note
    assert entry.message == "Merged 2 spellings: spark → Apache Spark, postgres → PostgreSQL"


def test_bad_output_leaves_aliases_empty_and_raises_the_caveat_but_good_output_does_not():
    deps, *_ = make_deps(cheap=["bad", "bad"])
    update = run_normalise(deps, a=extraction("Spark"))
    assert update["skill_aliases"] == {}
    assert [(e.kind, e.message.split(":")[0]) for e in update["run_log"]] == [(LogKind.caveat, "Skills merged by spelling only")]

    deps, *_ = make_deps(cheap=[groups(("Apache Spark", ["spark"]))])
    update = run_normalise(deps, a=extraction("Spark"))
    assert LogKind.caveat not in {e.kind for e in update["run_log"]}


def test_a_transient_failure_propagates():
    deps, *_ = make_deps(cheap=[httpx.ConnectError("down")] * 3)
    with pytest.raises(LLMExhausted):
        run_normalise(deps, a=extraction("Spark"))
