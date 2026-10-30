import asyncio
import copy
import json
import logging
from datetime import date
from pathlib import Path

import httpx
import pytest

from talent_scout.gateway import http
from talent_scout.gateway.adzuna import AdzunaClient
from talent_scout.gateway.gateway import make_gateway
from talent_scout.gateway.testing import FakeGateway
from talent_scout.gateway.types import CacheStatus, Fetch, FetchResult, GatewayError, SourceOutcome, SourceRejected, SourceUnavailable
from talent_scout.kernel.settings import Settings
from talent_scout.kernel.types import Source

FIXTURES = Path(__file__).parent / "fixtures" / "jobs"
APP_ID, APP_KEY = "test-app-id", "test-secret-key"


def fixture_body(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))["body"]


def make_settings():
    return Settings(
        _env_file=None, openrouter_api_key="k", adzuna_app_id=APP_ID, ADZUNA_API_KEY=APP_KEY, usajobs_api_key="c",
        usajobs_user_agent="d", langsmith_api_key="e", langsmith_tracing=False, langsmith_project="p",
    )


def make_fetch(**kw):
    base = dict(title="data engineer", country="us", location="", radius_km=0, max_days_old=30, category=None)
    return Fetch(**{**base, **kw})


def serve(body, status=200, seen=None):
    def handler(request):
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=body)

    return handler


def run_fetch(handler, f=None):
    async def go():
        async with make_gateway(make_settings(), transport=httpx.MockTransport(handler)) as gw:
            return await gw.fetch(f or make_fetch())

    return asyncio.run(go())


def run_search(handler, f=None):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await AdzunaClient(client, make_settings()).search(f or make_fetch())

    return asyncio.run(go())


def raw_result(**over):
    r = copy.deepcopy(fixture_body("adzuna_search")["results"][0])
    r.update(over)
    return r


def map_one(**over):
    """Serves one hand-edited result and returns the Postings fetch gives back."""
    out = run_fetch(serve({"count": 1, "results": [raw_result(**over)]}))
    return out.postings[0] if out.postings else None


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    monkeypatch.setattr(http, "_DELAYS", (0, 0))


# --- mapping ---

def test_search_fixture_gives_50_postings_with_mapped_fields():
    out = run_fetch(serve(fixture_body("adzuna_search")))
    assert len(out.postings) + sum(len(v) for v in out.merged.values()) == 50
    assert out.sources[Source.adzuna].total == 3200
    assert out.sources[Source.adzuna].dropped == 0
    p = out.postings[0]
    assert p.source == Source.adzuna and p.salary.predicted and p.salary.currency == "USD"
    assert p.posted_at == date(2026, 10, 14)
    assert p.region == ("US", "New York", "New York City", "Manhattan", "Grand Central")
    assert all("utm_" not in q.url for q in out.postings)
    assert "se=" in p.url and "v=" in p.url


def test_non_domain_tags_map_to_none_and_real_tags_stay():
    assert map_one(category={"tag": "it-jobs", "label": "IT Jobs"}).domain == "it-jobs"
    for tag in ("graduate-jobs", "part-time-jobs", "other-general-jobs", "unknown"):
        assert map_one(category={"tag": tag}).domain is None
    r = raw_result()
    del r["category"]
    out = run_fetch(serve({"count": 1, "results": [r]}))
    assert out.postings[0].domain is None


@pytest.mark.parametrize(
    "lo, hi, expected",
    [
        (200.0, 100.0, (100.0, 200.0)),  # reversed is swapped
        (None, 150.0, (None, 150.0)),
        (150.0, None, (150.0, None)),
        (0, 150.0, (None, 150.0)),  # a non-positive bound counts as missing
    ],
)
def test_salary_bounds(lo, hi, expected):
    r = raw_result(salary_min=lo, salary_max=hi)
    for k in ("salary_min", "salary_max"):
        if r[k] is None:
            del r[k]
    p = run_fetch(serve({"count": 1, "results": [r]})).postings[0]
    assert (p.salary.min, p.salary.max) == expected
    assert p.salary.period == "unknown"


def test_no_usable_salary_is_none():
    r = raw_result(salary_min=0, salary_max=-5)
    assert run_fetch(serve({"count": 1, "results": [r]})).postings[0].salary is None
    del r["salary_min"], r["salary_max"]
    assert run_fetch(serve({"count": 1, "results": [r]})).postings[0].salary is None


@pytest.mark.parametrize("flag, predicted", [("1", True), (1, True), ("0", False), (None, False)])
def test_predicted_flag_accepts_string_and_int(flag, predicted):
    assert map_one(salary_is_predicted=flag).salary.predicted is predicted


def test_missing_company_and_area_are_not_drops():
    r = raw_result()
    del r["company"]
    r["location"] = {"display_name": "Somewhere"}
    out = run_fetch(serve({"count": 1, "results": [r]}))
    assert out.sources[Source.adzuna].dropped == 0
    assert out.postings[0].company is None
    assert out.postings[0].region == ("US",)


def test_bad_result_is_counted_in_dropped_and_the_rest_return():
    bad = raw_result()
    del bad["id"]
    good = raw_result(id="42", title="Other Role")
    out = run_fetch(serve({"count": 2, "results": [bad, good]}))
    assert [p.source_id for p in out.postings] == ["42"]
    assert out.sources[Source.adzuna].dropped == 1


def test_text_is_trimmed_and_collapsed():
    p = map_one(title="  Data \n Engineer ", description=" a   b…")
    assert (p.title, p.description) == ("Data Engineer", "a b…")


# --- request ---

def test_request_params_for_a_located_search():
    seen = []
    run_fetch(serve(fixture_body("adzuna_search"), seen=seen), make_fetch(location="Washington", radius_km=25, category="it-jobs", page=2))
    req = seen[0]
    assert req.url.path == "/v1/api/jobs/us/search/2"
    q = dict(req.url.params)
    assert q == {
        "app_id": APP_ID, "app_key": APP_KEY, "title_only": "data engineer", "results_per_page": "50",
        "max_days_old": "30", "sort_by": "date", "where": "washington", "distance": "25", "category": "it-jobs",
    }


def test_blank_location_omits_where_and_distance():
    seen = []
    run_fetch(serve(fixture_body("adzuna_search"), seen=seen), make_fetch(radius_km=25))
    assert "where" not in seen[0].url.params and "distance" not in seen[0].url.params
    assert "category" not in seen[0].url.params


# --- coalescing through fetch ---

def test_deloitte_and_capital_one_collapse_and_booz_allen_stays_apart():
    ny = run_fetch(serve(fixture_body("adzuna_search")))
    by = lambda out, company, title: [p for p in out.postings if p.company == company and p.title == title]

    (deloitte,) = by(ny, "Deloitte", "Data Engineer III")
    assert deloitte.key == "adzuna:5920497025"  # same date on all three, so the lowest key wins
    assert ny.merged[deloitte.key] == ["adzuna:5920529705", "adzuna:5920529706"]

    (capital,) = by(ny, "Capital One", "Data Engineer 4")
    assert capital.key == "adzuna:5916901021"  # the newest repost
    assert ny.merged[capital.key] == ["adzuna:5909951202", "adzuna:5905486753"]

    dc = run_fetch(serve(fixture_body("adzuna_search_dc")))
    assert len(by(dc, "Booz Allen Hamilton", "Data Engineer")) == 15


# --- failures ---

def test_timeout_connect_error_and_5xx_retry_twice_then_fail():
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)

    def refused(request):
        raise httpx.ConnectError("no route", request=request)

    for fail in (timeout, refused, serve({}, status=503)):
        calls = []

        def handler(request, fail=fail):
            calls.append(1)
            return fail(request)

        with pytest.raises(GatewayError):
            run_fetch(handler)
        assert len(calls) == 3


def test_no_source_answering_raises_gateway_error():
    with pytest.raises(GatewayError, match="adzuna"):
        run_fetch(serve({}, status=500))


def test_body_without_results_is_source_unavailable():
    for body in ({"count": 3}, {"results": "nope", "count": 3}, ["x"]):
        with pytest.raises(SourceUnavailable):
            run_search(serve(body))
    with pytest.raises(SourceUnavailable):
        run_search(lambda request: httpx.Response(200, text="<html>not json</html>"))


def test_401_raises_source_rejected_without_key_or_url():
    with pytest.raises(SourceRejected) as e:
        run_fetch(serve({"error": "bad credentials"}, status=401))
    err = e.value
    assert (err.source, err.status) == (Source.adzuna, 401)
    assert "bad credentials" in err.body
    text = str(err)
    assert APP_KEY not in text and APP_ID not in text and "adzuna.com" not in text


def test_5xx_failure_text_is_fixed_and_hides_the_cause():
    with pytest.raises(SourceUnavailable) as e:
        run_search(serve({}, status=500))
    assert e.value.__cause__ is None and e.value.__suppress_context__
    assert APP_KEY not in str(e.value) and "http" not in str(e.value)


def test_raise_for_status_is_never_called():
    src = Path(http.__file__).parent
    assert not any("raise_for_status" in p.read_text(encoding="utf-8") for p in src.glob("*.py"))


def test_make_gateway_quiets_the_httpx_logger():
    logging.getLogger("httpx").setLevel(logging.INFO)
    make_gateway(make_settings())
    assert logging.getLogger("httpx").level == logging.WARNING


# --- test fake ---

def test_fake_gateway_returns_canned_results_in_order():
    outcome = SourceOutcome(total=1, dropped=0, cache=CacheStatus.miss, fetched_at="2026-10-30T00:00:00Z", calls_left=None)
    first = FetchResult(postings=[], merged={}, sources={Source.adzuna: outcome}, failures={})
    second = FetchResult(postings=[], merged={}, sources={}, failures={Source.adzuna: "down"})

    async def go():
        async with FakeGateway([first, second]) as gw:
            return await gw.fetch(make_fetch()), await gw.fetch(make_fetch(page=2))

    assert asyncio.run(go()) == (first, second)
