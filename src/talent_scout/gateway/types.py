from datetime import datetime
from enum import StrEnum
from typing import NamedTuple

from pydantic import Field, field_validator

from talent_scout.kernel.types import Model, Posting, Source

ADZUNA_CURRENCY = {
    "gb": "GBP", "us": "USD", "ca": "CAD", "au": "AUD", "nz": "NZD", "in": "INR", "sg": "SGD",
    "za": "ZAR", "br": "BRL", "mx": "MXN", "pl": "PLN", "ch": "CHF",
    "at": "EUR", "be": "EUR", "de": "EUR", "es": "EUR", "fr": "EUR", "it": "EUR", "nl": "EUR",
}

ATTRIBUTION = {Source.adzuna: "The Adzuna API"}


class GatewayError(Exception):
    pass


class BudgetExhausted(GatewayError):
    pass


class SourceUnavailable(GatewayError):
    pass


class SourceRejected(Exception):
    """A 4xx from a source. Carries the response body but never the URL, which holds the Adzuna keys."""

    def __init__(self, source: Source, status: int, body: str):
        super().__init__(f"{source} rejected the request with {status}: {body}")
        self.source, self.status, self.body = source, status, body


class Fetch(Model):
    title: str
    country: str
    location: str  # blank = country-wide
    radius_km: int = Field(ge=0)
    max_days_old: int = Field(ge=1)
    category: str | None
    page: int = Field(1, ge=1)

    # Equal Fetches must be equal objects: the dumped JSON is the cache key.
    @field_validator("title", "location", "category")
    @classmethod
    def _normalise(cls, v, info):
        if v is None:
            return v
        v = " ".join(v.lower().split())
        if info.field_name == "title" and not v:
            raise ValueError("title must not be blank")
        return v

    # An unknown country is a planning bug, not a source failure, so it fails here.
    @field_validator("country")
    @classmethod
    def _known_country(cls, v):
        if v not in ADZUNA_CURRENCY:
            raise ValueError(f"country {v!r} is not one Adzuna serves")
        return v


class CacheStatus(StrEnum):
    hit = "hit"
    miss = "miss"
    replay = "replay"
    store = "store"


class SourceOutcome(Model):
    total: int
    dropped: int
    cache: CacheStatus
    fetched_at: datetime
    calls_left: int | None


class FetchResult(Model):
    postings: list[Posting]
    merged: dict[str, list[str]]
    sources: dict[Source, SourceOutcome]
    failures: dict[Source, str]


class Page(NamedTuple):
    postings: list[Posting]
    total: int
    dropped: int
