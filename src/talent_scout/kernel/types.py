from datetime import date
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

# Constraints live in the type so every model using them rejects the same bad values.
NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Source(StrEnum):
    adzuna = "adzuna"
    usajobs = "usajobs"


class PayPeriod(StrEnum):
    annual = "annual"
    monthly = "monthly"
    biweekly = "biweekly"
    weekly = "weekly"
    daily = "daily"
    hourly = "hourly"
    unknown = "unknown"


class Salary(Model):
    min: float | None
    max: float | None
    currency: CurrencyCode
    period: PayPeriod
    predicted: bool

    @model_validator(mode="after")
    def _check_bounds(self):
        if self.min is None and self.max is None:
            raise ValueError("salary needs at least one of min or max")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError(f"salary min {self.min} is above max {self.max}")
        return self


class Posting(Model):
    source: Source
    source_id: str
    title: str
    company: str | None
    location: str
    region: tuple[str, ...]
    domain: str | None
    posted_at: date
    closes_at: date | None
    description: str
    url: str
    salary: Salary | None

    # A property, not a computed_field: dumped data must stay valid input under extra="forbid".
    @property
    def key(self) -> str:
        return f"{self.source}:{self.source_id}"


class WorkMode(StrEnum):
    onsite = "onsite"
    hybrid = "hybrid"
    remote = "remote"


class RequestField(StrEnum):
    role = "role"
    location = "location"
    seniority = "seniority"
    employment_type = "employment_type"
    work_mode = "work_mode"
    currency = "currency"
    purpose = "purpose"


class HiringRequest(Model):
    role: NonBlank = Field(description="The job title or role being hired for.")
    location: NonBlank = Field(description="Where the hire will work, as the user gave it.")
    seniority: str | None = Field(description="Seniority level, e.g. junior or senior; null if not stated.")
    employment_type: str | None = Field(description="e.g. full-time, contract; null if not stated.")
    work_mode: WorkMode | None = Field(description="onsite, hybrid or remote; null if not stated.")
    currency: CurrencyCode | None = Field(description="ISO 4217 currency the user wants pay shown in; null if not stated.")
    purpose: str | None = Field(description="Why the user wants this market view; null if not stated.")


class ClarifyingQuestion(Model):
    about: RequestField = Field(description="The request field this question tries to pin down.")
    text: str = Field(description="The question to put to the user.")
    options: list[str] = Field(description="Suggested answers; empty if the question is open-ended.")
    answer: str | None = Field(description="The user's answer. Filled by code, always null from the model.")


class Assumption(Model):
    about: RequestField = Field(description="The request field this assumption fills in.")
    value: str = Field(description="The value assumed for that field.")
    reason: str = Field(description="Why this value was assumed.")


class SearchPlan(Model):
    titles: list[str] = Field(min_length=1, description="Job titles to search for, primary title first.")
    country: str = Field(pattern=r"^[a-z]{2}$", description="Lowercase two-letter country code, e.g. us.")
    location: str = Field(description="Place to search around, as a source-friendly name.")
    radius_km: int = Field(ge=0, description="Search radius around the location, in kilometres.")
    max_days_old: int = Field(ge=1, description="Ignore postings older than this many days.")
    target_postings: int = Field(ge=1, description="How many relevant postings are enough for analysis.")
    category: str | None = Field(description="Source job category to narrow the search; null for none.")


class Dimension(StrEnum):
    demand = "demand"
    compensation = "compensation"
    skills = "skills"
    competition = "competition"
    titles_seniority = "titles_seniority"


class Evidence(Model):
    posting_keys: list[str]

    @field_validator("posting_keys")
    @classmethod
    def _sort_dedupe(cls, keys: list[str]) -> list[str]:
        return sorted(set(keys))

    # A property for the same reason as Posting.key: it stays out of model_dump.
    @property
    def count(self) -> int:
        return len(self.posting_keys)


class Stat(Model):
    id: str
    dimension: Dimension
    label: str
    value: float | str
    unit: str | None
    evidence: Evidence


class MarketStats(Model):
    sample_size: int
    stats: list[Stat]

    @field_validator("stats")
    @classmethod
    def _unique_ids(cls, stats: list[Stat]) -> list[Stat]:
        ids = [s.id for s in stats]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate stat ids: {dupes}")
        return stats
