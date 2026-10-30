import pytest
from pydantic import ValidationError

from talent_scout.kernel.settings import Settings, get_settings

REQUIRED = {
    "openrouter_api_key": "k",
    "adzuna_app_id": "id",
    "ADZUNA_API_KEY": "adz",
    "usajobs_api_key": "k",
    "usajobs_user_agent": "ua",
    "langsmith_api_key": "k",
    "langsmith_tracing": True,
    "langsmith_project": "p",
}


def make(**over):
    return Settings(_env_file=None, **{**REQUIRED, **over})


def test_max_tokens_floor_rejects_999():
    with pytest.raises(ValidationError):
        make(max_tokens_cheap=999)


def test_comma_list_parses_into_chain(monkeypatch):
    monkeypatch.setenv("LLM_CHEAP", "a/x, b/y")
    assert make().llm_cheap == ["a/x", "b/y"]


def test_adzuna_api_key_populates_app_key(monkeypatch):
    monkeypatch.setenv("ADZUNA_API_KEY", "from-env")
    s = Settings(_env_file=None, **{k: v for k, v in REQUIRED.items() if k != "ADZUNA_API_KEY"})
    assert s.adzuna_app_key == "from-env"


def test_real_env_loads_cached_and_exports_langsmith(monkeypatch):
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    get_settings.cache_clear()
    s = get_settings()
    assert get_settings() is s
    import os

    assert os.environ["LANGSMITH_PROJECT"] == s.langsmith_project
