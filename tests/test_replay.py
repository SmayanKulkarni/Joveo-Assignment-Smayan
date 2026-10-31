import asyncio

import pytest
from langchain_core.globals import get_llm_cache, set_llm_cache
from langchain_core.messages import AIMessage
from langchain_typesafe import Noul
from pydantic import Field

from talent_scout.kernel import llm
from talent_scout.kernel.jev import Jev
from talent_scout.kernel.llm import LLMExhausted, make_tiers
from talent_scout.kernel.replay import Replay, install_llm_cache
from talent_scout.kernel.testing import fake_classifier
from talent_scout.kernel.thresholds import CUTS
from test_llm import GOOD, Out, Scripted, http_error, make_settings, tiers
from openrouter.errors import BadRequestResponseError


class Named(Scripted):
    model_name: str = "a"

    @property
    def _identifying_params(self):
        return {"model_name": self.model_name}


def named(name, *script):
    return Named(messages=iter([]), script=list(script), model_name=name)


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setattr(llm, "_BACKOFF", False)
    yield
    set_llm_cache(None)


@pytest.fixture
def replay(tmp_path):
    r = Replay(tmp_path / "replay.sqlite")
    set_llm_cache(r.llm)
    return r


def run(t, text="hi", system="sys"):
    return asyncio.run(t.structured("cheap", Out, system=system, name="t").ainvoke(text))


def test_repeated_structured_call_hits_the_model_once(replay):
    m = named("a", GOOD)
    assert run(tiers(m)) == run(tiers(m)) == Out(n=3)
    assert len(m.seen) == 1


def test_changed_prompt_or_model_misses(replay):
    m = named("a", GOOD, GOOD, GOOD)
    run(tiers(m))
    run(tiers(m), text="other")
    run(tiers(m), system="other sys")
    other = named("b", GOOD)
    run(tiers(other))
    assert len(m.seen) == 3 and len(other.seen) == 1


def test_feedback_retry_misses_the_cache(replay):
    # First run caches "bad" for the original prompt, then dies before the retry's answer is cached.
    first = named("a", "bad", http_error(BadRequestResponseError, 400))
    with pytest.raises(BadRequestResponseError):
        run(tiers(first))
    second = named("a", GOOD)
    assert run(tiers(second)) == Out(n=3)
    assert len(second.seen) == 1


def test_a_cut_off_reply_is_not_stored_so_a_rerun_reaches_the_model(replay):
    cut_off = AIMessage(content='{"n":', response_metadata={"finish_reason": "length"})
    with pytest.raises(LLMExhausted):
        run(tiers(named("a", cut_off)))
    second = named("a", GOOD)
    assert run(tiers(second)) == Out(n=3)
    assert len(second.seen) == 1


def test_repeated_judge_hits_the_classifier_once(replay):
    fake = fake_classifier({"q": 1})
    jev = Jev(fake, CUTS, replay)
    q = {"q": Noul(instructions="Is this about software?")}
    for _ in range(2):
        assert asyncio.run(jev.judge("clarity", {"t": "x"}, q))["q"].outcome is True
    assert len(fake.calls) == 1
    asyncio.run(jev.judge("clarity", {"t": "x"}, {"q": Noul(instructions="Different question?")}))
    assert len(fake.calls) == 2


def test_unset_installs_nothing_and_creates_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_tiers(make_settings())
    install_llm_cache(make_settings())
    assert get_llm_cache() is None and list(tmp_path.iterdir()) == []


def test_set_installs_the_cache(tmp_path):
    make_tiers(make_settings(replay_cache=tmp_path / "r.sqlite"))
    assert get_llm_cache() is not None and (tmp_path / "r.sqlite").exists()
