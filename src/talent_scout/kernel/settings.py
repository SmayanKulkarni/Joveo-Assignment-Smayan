import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_ENV, extra="ignore", frozen=True, populate_by_name=True
    )

    openrouter_api_key: str
    adzuna_app_id: str
    # .env already names this ADZUNA_API_KEY, so the LLD's field name is kept via an alias.
    adzuna_app_key: str = Field(validation_alias="ADZUNA_API_KEY")
    usajobs_api_key: str
    usajobs_user_agent: str
    langsmith_api_key: str
    langsmith_tracing: bool
    langsmith_project: str

    # NoDecode stops pydantic-settings parsing the .env value as JSON, so the comma list reaches the validator.
    llm_cheap: Annotated[list[str], NoDecode] = [
        "deepseek/deepseek-v4.1-flash",
        "minimax/minimax-m3.1-flash",
    ]
    llm_strong: Annotated[list[str], NoDecode] = [
        "deepseek/deepseek-v4.1-flash",
        "minimax/minimax-m3.1-flash",
    ]
    reasoning_cheap: str = "low"
    reasoning_strong: str = "medium"
    max_tokens_cheap: int = Field(2048, ge=1000)
    max_tokens_strong: int = Field(8192, ge=1000)
    llm_concurrency: int = 20
    jev_concurrency: int = 8
    balance_floor_usd: float = 0.25
    replay_cache: Path | None = None
    gateway_db: Path = Path(".cache/gateway.sqlite")
    adzuna_daily_limit: int = 25
    l1_ttl_hours: int = 24

    @field_validator("llm_cheap", "llm_strong", mode="before")
    @classmethod
    def _split_chain(cls, v):
        if isinstance(v, str):
            return [m.strip() for m in v.split(",") if m.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # LangSmith caches its env vars on first use, so export them before any LangChain call.
    os.environ["LANGSMITH_API_KEY"] = s.langsmith_api_key
    os.environ["LANGSMITH_TRACING"] = str(s.langsmith_tracing).lower()
    os.environ["LANGSMITH_PROJECT"] = s.langsmith_project
    return s
