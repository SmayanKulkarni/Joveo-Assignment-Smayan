import logging
from datetime import UTC, datetime
from urllib.parse import urlsplit, urlunsplit

import httpx

from talent_scout.gateway.http import get_json
from talent_scout.gateway.store import Store
from talent_scout.gateway.types import ADZUNA_CURRENCY, Fetch, Page, SourceUnavailable
from talent_scout.kernel.settings import Settings
from talent_scout.kernel.types import Posting, Salary, Source

log = logging.getLogger(__name__)

BASE = "https://api.adzuna.com/v1/api/jobs"
PAGE_SIZE = 50  # Adzuna silently caps at 50
NOT_DOMAINS = {"graduate-jobs", "part-time-jobs", "other-general-jobs", "unknown"}
# utm_source is our app id; every other param may be needed by the landing page.
TRACKING = {"utm_source", "utm_medium"}


def collapse(s: str) -> str:
    return " ".join(s.split())


def _url(url: str) -> str:
    u = urlsplit(url)
    # Filter the raw pairs rather than re-encoding them: the landing page's signed params must stay byte-exact.
    query = "&".join(p for p in u.query.split("&") if p.split("=", 1)[0] not in TRACKING)
    return urlunsplit(u._replace(query=query))


def _salary(raw: dict, country: str) -> Salary | None:
    lo, hi = (b if b and b > 0 else None for b in (raw.get("salary_min"), raw.get("salary_max")))
    if lo is None and hi is None:
        return None
    if lo is not None and hi is not None and lo > hi:
        lo, hi = hi, lo
    return Salary(
        min=lo, max=hi, currency=ADZUNA_CURRENCY[country], period="unknown",
        predicted=str(raw.get("salary_is_predicted")) == "1",
    )


def _map(raw: dict, country: str) -> Posting:
    company = (raw.get("company") or {}).get("display_name")
    tag = (raw.get("category") or {}).get("tag")
    location = raw["location"]
    created = datetime.fromisoformat(raw["created"])
    return Posting(
        source=Source.adzuna,
        source_id=str(raw["id"]),
        title=collapse(raw["title"]),
        company=collapse(company) if company else None,
        location=location["display_name"],
        region=tuple(location.get("area") or (country.upper(),)),
        domain=None if tag in NOT_DOMAINS else tag,
        # A timestamp with no zone is taken as UTC; astimezone alone would read it as local time.
        posted_at=created.replace(tzinfo=created.tzinfo or UTC).astimezone(UTC).date(),
        closes_at=None,
        description=collapse(raw["description"]),
        url=_url(raw["redirect_url"]),
        salary=_salary(raw, country),
    )


class AdzunaClient:
    def __init__(self, client: httpx.AsyncClient, settings: Settings, store: Store):
        self._client, self._settings, self._store = client, settings, store

    async def search(self, f: Fetch) -> Page:
        params = {
            "app_id": self._settings.adzuna_app_id,
            "app_key": self._settings.adzuna_app_key,
            "title_only": f.title,  # never `what`: matching the title cuts keyword collisions
            "results_per_page": PAGE_SIZE,
            "max_days_old": f.max_days_old,
            "sort_by": "date",  # page N walks back in time
        }
        if f.location:
            params |= {"where": f.location, "distance": f.radius_km}
        if f.category:
            params["category"] = f.category

        body = await get_json(self._client, Source.adzuna, f"{BASE}/{f.country}/search/{f.page}", self._store, params=params)
        if not (isinstance(body, dict) and isinstance(body.get("results"), list) and isinstance(body.get("count"), int)):
            raise SourceUnavailable("adzuna returned a body without results") from None

        postings, dropped = [], 0
        for raw in body["results"]:
            try:
                postings.append(_map(raw, f.country))
            except (KeyError, TypeError, ValueError):  # ValueError covers pydantic's ValidationError
                dropped += 1
                log.warning("dropped adzuna result %s", raw.get("id") if isinstance(raw, dict) else None)
        return Page(postings, body["count"], dropped)
