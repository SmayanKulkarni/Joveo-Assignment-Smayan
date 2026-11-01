from typing import Literal

from talent_scout.gateway.types import Fetch, FetchResult
from talent_scout.kernel.types import Model, SearchPlan, Source


class FetchRecord(Model):
    attempt: int  # len(broadened_plans) when it ran
    source: Source  # the tool the model called
    fetch: Fetch
    result: FetchResult | None  # None when the source failed
    error: str | None  # the GatewayError text


class LowDataPayload(Model):
    count: int  # len(sample)
    target: int
    attempts: int
    plans: list[SearchPlan]  # every plan tried, oldest first
    fetched: int  # len(postings)
    rejected: int
    calls_left: int | None  # Adzuna's, at the moment of the Pause
    blocked: str | None  # fetch_blocked


class LowDataAnswer(Model):
    action: Literal["broaden", "continue", "abort"]
    guidance: str | None = None  # feeds the next broaden
    whole_country: bool = False  # the only way to drop the place; ignored by every other action
