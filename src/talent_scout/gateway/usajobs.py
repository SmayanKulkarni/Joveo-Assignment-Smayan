import logging
from datetime import date
from functools import cache
from math import ceil, inf

import httpx

from talent_scout.gateway.adzuna import collapse
from talent_scout.gateway.http import get_json
from talent_scout.gateway.store import Store
from talent_scout.gateway.types import Fetch, Page, SourceUnavailable
from talent_scout.kernel.settings import Settings
from talent_scout.kernel.types import Posting, Salary, Source

log = logging.getLogger(__name__)

URL = "https://data.usajobs.gov/api/Search"
HOST = "data.usajobs.gov"
PAGE_SIZE = 50
MAX_DATE_POSTED = 60  # the API silently caps DatePosted here
KM_PER_MILE = 1.609  # Radius behaves like miles
MAX_DESCRIPTION = 4000

# Codes that give a comparable figure; anything else (SY, PW, FB, ST, WC) leaves the salary empty.
PERIODS = {"PA": "annual", "PH": "hourly", "PD": "daily", "BW": "biweekly", "PM": "monthly"}

# Domain tag -> (series families, series overrides). A series override wins over its family; None means no Domain.
DOMAINS = {
    "social-work-jobs": ("0100", ""),
    "hr-jobs": ("0200", ""),
    "admin-jobs": ("0300", ""),
    "scientific-qa-jobs": ("0400 1300 1500 1900", "0028"),
    "accounting-finance-jobs": ("0500", "1510"),
    "healthcare-nursing-jobs": ("0600 0700", "0180"),
    "engineering-jobs": ("0800", ""),
    "legal-jobs": ("0900 1200", ""),
    "creative-design-jobs": ("1000 3900 9000", ""),
    "pr-advertising-marketing-jobs": ("", "1035"),
    "consultancy-jobs": ("1100", "0110 0343"),
    "property-jobs": ("", "1170"),
    # 8999 is the one series whose family is not its first two digits plus 00 (it would be 8900).
    "maintenance-jobs": ("1600 4800 5300 5800 8200 8600 8800", "8999"),
    "teaching-jobs": ("1700", ""),
    "logistics-warehouse-jobs": ("2000 2100 5700 6900 7000", ""),
    "it-jobs": ("2200", "0391 0854 1550 1560"),
    "trade-construction-jobs": ("2500 2600 2800 3600 3800 4100 4200 4600 4700", ""),
    "manufacturing-jobs": ("3100 3300 3400 3700 4000 4300 4400 5200 5400 6500 6600", ""),
    "domestic-help-cleaning-jobs": ("7300", ""),
    "hospitality-catering-jobs": ("7400", ""),
    None: ("0000 1400 1800 2300 3500 5000 7600 9900", "1102 1105"),
}
FAMILIES = {code: tag for tag, (families, _) in DOMAINS.items() for code in families.split()}
OVERRIDES = {code: tag for tag, (_, overrides) in DOMAINS.items() for code in overrides.split()}


@cache  # so an unknown series is logged once, not once per Posting
def _domain(series: str | None) -> str | None:
    if not series:
        return None
    if series in OVERRIDES:
        return OVERRIDES[series]
    if series[:2] + "00" in FAMILIES:
        return FAMILIES[series[:2] + "00"]
    log.warning("unknown usajobs series %s", series)
    return None


def _region(locations: list[dict]) -> tuple[str, ...]:
    paths = []
    for loc in locations:
        country = "US" if loc["CountryCode"] == "United States" else loc["CountryCode"]
        state = loc.get("CountrySubDivisionCode", "")
        # CityName repeats the state ("Washington, District of Columbia"), which the path already holds.
        city = loc.get("CityName", "").removesuffix(f", {state}") if state else loc.get("CityName", "")
        paths.append(tuple(part for part in (country, state, city) if part))
    # Several sites share only what they have in common, so FAA's 1,176 locations end up as just the country.
    common = []
    for parts in zip(*paths):
        if len(set(parts)) > 1:
            break
        common.append(parts[0])
    return tuple(common) or ("US",)


def _salary(d: dict) -> Salary | None:
    pay = (d.get("PositionRemuneration") or [None])[0]  # only the first entry
    period = pay and PERIODS.get(pay["RateIntervalCode"])
    if not period:
        return None
    lo, hi = (v if 0 < v < inf else None for v in (float(pay.get("MinimumRange") or 0), float(pay.get("MaximumRange") or 0)))
    if lo is None and hi is None:
        return None
    if lo is not None and hi is not None and lo > hi:
        lo, hi = hi, lo
    return Salary(min=lo, max=hi, currency="USD", period=period, predicted=False)


def _description(d: dict) -> str:
    details = (d.get("UserArea") or {}).get("Details") or {}
    duties = details.get("MajorDuties") or []
    parts = [details.get("JobSummary"), *([duties] if isinstance(duties, str) else duties), d.get("QualificationSummary")]
    text = collapse(" ".join(p for p in parts if p))[:MAX_DESCRIPTION]
    # An empty description is a prefix of every other, so coalesce would merge it with any Posting of the same job title.
    if not text:
        raise ValueError("blank description")
    return text


def _date(s: str) -> date:
    return date.fromisoformat(s[:10])  # no timezone in the field, so the date is taken as written


def _closes_at(d: dict) -> date | None:
    try:
        return _date(d["ApplicationCloseDate"])
    except (KeyError, TypeError, ValueError):
        return None


def _map(item: dict) -> Posting:
    d = item["MatchedObjectDescriptor"]
    series = ((d.get("JobCategory") or [{}])[0]).get("Code")
    return Posting(
        source=Source.usajobs,
        source_id=str(item["MatchedObjectId"]),
        title=collapse(d["PositionTitle"]),
        company=collapse(d["OrganizationName"]),  # the agency, not the department
        location=d["PositionLocationDisplay"],
        region=_region(d.get("PositionLocation") or []),
        domain=_domain(series),
        posted_at=_date(d["PublicationStartDate"]),
        closes_at=_closes_at(d),
        description=_description(d),
        url=d["PositionURI"].replace(":443/", "/", 1),
        salary=_salary(d),
    )


class UsajobsClient:
    def __init__(self, client: httpx.AsyncClient, settings: Settings, store: Store):
        self._client, self._settings, self._store = client, settings, store

    async def search(self, f: Fetch) -> Page:
        # Fetch.category is not sent: filtering after mapping would shorten pages and falsify the total.
        params = {
            "PositionTitle": f.title,
            "ResultsPerPage": PAGE_SIZE,
            "Page": f.page,
            "DatePosted": min(f.max_days_old, MAX_DATE_POSTED),
        }
        if f.location:
            params |= {"LocationName": f.location, "Radius": ceil(f.radius_km / KM_PER_MILE)}
        headers = {"Host": HOST, "User-Agent": self._settings.usajobs_user_agent, "Authorization-Key": self._settings.usajobs_api_key}

        body = await get_json(self._client, Source.usajobs, URL, self._store, params=params, headers=headers)
        result = body.get("SearchResult") if isinstance(body, dict) else None
        if not (
            isinstance(result, dict)
            and isinstance(result.get("SearchResultItems"), list)
            and isinstance(result.get("SearchResultCountAll"), int)
        ):
            raise SourceUnavailable("usajobs returned a body without SearchResult") from None

        postings, dropped = [], 0
        for item in result["SearchResultItems"]:
            try:
                postings.append(_map(item))
            except (KeyError, TypeError, ValueError):  # ValueError covers pydantic's ValidationError
                dropped += 1
                log.warning("dropped usajobs result %s", item.get("MatchedObjectId") if isinstance(item, dict) else None)
        return Page(postings, result["SearchResultCountAll"], dropped)
