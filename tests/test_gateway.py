import asyncio
import copy
import json
import logging
import sqlite3
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from talent_scout.gateway import http
from talent_scout.gateway.adzuna import AdzunaClient
from talent_scout.gateway.gateway import make_gateway
from talent_scout.gateway.store import Store
from talent_scout.gateway.testing import FakeGateway
from talent_scout.gateway.types import BudgetExhausted, CacheStatus, Fetch, FetchResult, GatewayError, SourceOutcome, SourceRejected, SourceUnavailable
from talent_scout.kernel.testing import make_settings
from talent_scout.kernel.types import Source

FIXTURES = Path(__file__).parent / "fixtures" / "jobs"
APP_ID, APP_KEY = "test-app-id", "test-secret-key"


def fixture_body(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))["body"]


def gateway_settings(**kw):
    return make_settings(adzuna_app_id=APP_ID, ADZUNA_API_KEY=APP_KEY, **kw)


def make_fetch(**kw):
    base = dict(title="data engineer", country="us", location="", radius_km=0, max_days_old=30, category=None)
    return Fetch(**{**base, **kw})


def serve(body, status=200, seen=None):
    def handler(request):
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=body)

    return handler


def run_all(handler, *fetches, settings=None):
    """Fetches in order through one open gateway."""
    async def go():
        async with make_gateway(settings or gateway_settings(), transport=httpx.MockTransport(handler)) as gw:
            return [await gw.fetch(f) for f in fetches]

    return asyncio.run(go())


def rerun(handler, f=None, settings=None):
    """One fetch against whatever gateway_db already holds, like a restarted process."""
    return run_all(handler, f or make_fetch(), settings=settings)[0]


def run_fetch(handler, f=None, settings=None):
    # Starts from an empty gateway_db, so serving a different body for the same Fetch never meets an old L1 row.
    (settings or gateway_settings()).gateway_db.unlink(missing_ok=True)
    return rerun(handler, f, settings)


def run_search(handler, f=None):
    async def go():
        settings = gateway_settings()
        store = Store(settings)
        try:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await AdzunaClient(client, settings, store).search(f or make_fetch())
        finally:
            store.close()

    return asyncio.run(go())


def calls_left(settings=None):
    store = Store(settings or gateway_settings())
    try:
        return store.calls_left(Source.adzuna)
    finally:
        store.close()


def db_exec(sql, *args, settings=None):
    """Runs raw SQL on gateway_db through a second connection, as a killed-and-restarted process would."""
    db = sqlite3.connect((settings or gateway_settings()).gateway_db)
    try:
        rows = db.execute(sql, args).fetchall()
        db.commit()
        return rows
    finally:
        db.close()


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


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    # The default gateway_db is relative, so every test gets its own file without touching the repo's .cache.
    monkeypatch.chdir(tmp_path)


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


def test_created_without_a_zone_is_read_as_utc():
    assert map_one(created="2026-10-14T21:35:19").posted_at == date(2026, 10, 14)
    assert map_one(created="2026-10-14T21:35:19-05:00").posted_at == date(2026, 10, 15)


def test_redirect_url_keeps_other_params_byte_exact():
    url = "https://www.adzuna.com/land/ad/1?se=a%2Fb+c&utm_medium=api&utm_source=X&v=9F"
    assert map_one(redirect_url=url).url == "https://www.adzuna.com/land/ad/1?se=a%2Fb+c&v=9F"


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

    def dropped(request):
        raise httpx.ReadError("connection cut", request=request)

    for fail in (timeout, refused, dropped, serve({}, status=503)):
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


def test_adzuna_429_is_budget_exhausted_with_no_retry():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(429, json={})

    with pytest.raises(BudgetExhausted):
        run_search(handler)
    assert len(calls) == 1


def test_fetch_outside_async_with_is_a_usage_error():
    with pytest.raises(RuntimeError, match="async with"):
        asyncio.run(make_gateway(gateway_settings()).fetch(make_fetch()))


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
    make_gateway(gateway_settings())
    assert logging.getLogger("httpx").level == logging.WARNING


# --- L1 cache and budget guard ---

def test_repeat_fetch_is_a_hit_with_no_http_call_and_no_spend():
    seen = []
    first, second = run_all(serve(fixture_body("adzuna_search"), seen=seen), make_fetch(), make_fetch())
    assert len(seen) == 1
    a, b = first.sources[Source.adzuna], second.sources[Source.adzuna]
    assert (a.cache, b.cache) == (CacheStatus.miss, CacheStatus.hit)
    assert (a.calls_left, b.calls_left) == (24, 24)
    assert (a.total, a.dropped, a.fetched_at) == (b.total, b.dropped, b.fetched_at)
    assert second.postings == first.postings and second.merged == first.merged


def test_a_different_fetch_is_a_different_row():
    seen = []
    run_all(serve(fixture_body("adzuna_search"), seen=seen), make_fetch(), make_fetch(page=2))
    assert len(seen) == 2


def test_fresh_row_is_still_served_after_the_budget_has_run_out():
    settings = gateway_settings(adzuna_daily_limit=1)
    rerun(serve(fixture_body("adzuna_search")), settings=settings)
    seen = []
    out = rerun(serve({}, seen=seen), settings=settings)
    assert seen == [] and out.sources[Source.adzuna].cache == CacheStatus.hit
    assert out.sources[Source.adzuna].calls_left == 0


def backdate(hours):
    db_exec("UPDATE l1 SET fetched_at = ?", (datetime.now(UTC) - timedelta(hours=hours)).isoformat())


def test_row_past_the_ttl_misses_and_is_overwritten():
    rerun(serve({"count": 0, "results": []}))
    backdate(25)
    seen = []
    out = rerun(serve(fixture_body("adzuna_search"), seen=seen))
    assert len(seen) == 1 and out.sources[Source.adzuna].cache == CacheStatus.miss
    # Overwritten, so the next identical Fetch is served from the refreshed row.
    assert rerun(serve({}, seen=seen)).sources[Source.adzuna].cache == CacheStatus.hit
    assert len(seen) == 1


def test_row_just_inside_the_ttl_is_still_a_hit():
    rerun(serve(fixture_body("adzuna_search")))
    backdate(23)
    assert rerun(serve({})).sources[Source.adzuna].cache == CacheStatus.hit


def test_stale_row_is_not_served_when_the_budget_has_run_out():
    settings = gateway_settings(adzuna_daily_limit=1)
    rerun(serve(fixture_body("adzuna_search")), settings=settings)
    backdate(25)
    seen = []
    # With no other source the refusal surfaces as GatewayError; failures[adzuna] carries the same text.
    with pytest.raises(GatewayError, match="adzuna.*limit"):
        rerun(serve({}, seen=seen), settings=settings)
    assert seen == []


def test_row_that_no_longer_validates_is_a_miss():
    rerun(serve(fixture_body("adzuna_search")))
    db_exec("UPDATE l1 SET postings = ?", '[{"title": "old shape"}]')
    seen = []
    out = rerun(serve(fixture_body("adzuna_search"), seen=seen))
    assert len(seen) == 1 and out.sources[Source.adzuna].cache == CacheStatus.miss


def test_empty_result_list_is_cached_but_failures_and_bad_bodies_are_not():
    seen = []
    first, second = run_all(serve({"count": 0, "results": []}, seen=seen), make_fetch(), make_fetch())
    assert second.sources[Source.adzuna].cache == CacheStatus.hit and len(seen) == 1
    assert second.postings == []

    db_exec("DELETE FROM l1")
    for handler in (serve({}, status=500), serve({"count": 3}), serve({}, status=429)):
        with pytest.raises(GatewayError):
            rerun(handler)
    assert db_exec("SELECT COUNT(*) FROM l1") == [(0,)]


def test_rows_are_committed_before_fetch_returns_and_hold_no_credentials():
    async def go():
        async with make_gateway(gateway_settings(), transport=httpx.MockTransport(serve(fixture_body("adzuna_search")))) as gw:
            await gw.fetch(make_fetch())
            return db_exec("SELECT source, fetch, postings, expires_at FROM l1")  # a second connection, gateway still open

    ((source, key, postings, expires_at),) = asyncio.run(go())
    assert (source, expires_at) == ("adzuna", None)  # Adzuna has no close dates, so the row is never purged
    assert key == make_fetch().model_dump_json()
    for secret in (APP_ID, APP_KEY):
        assert secret not in key and secret not in postings


def test_guard_refuses_at_the_limit_and_the_count_survives_reopening():
    settings = gateway_settings(adzuna_daily_limit=2)
    store = Store(settings)
    store.spend(Source.adzuna)
    store.spend(Source.adzuna)
    with pytest.raises(BudgetExhausted):
        store.spend(Source.adzuna)
    store.close()

    reopened = Store(settings)
    with pytest.raises(BudgetExhausted):
        reopened.spend(Source.adzuna)
    assert reopened.calls_left(Source.adzuna) == 0
    # USAJOBS is counted but has no limit, so it reports unmetered.
    reopened.spend(Source.usajobs)
    assert reopened.calls_left(Source.usajobs) is None
    reopened.close()


def test_a_new_utc_day_starts_with_a_full_budget():
    settings = gateway_settings(adzuna_daily_limit=1)
    rerun(serve(fixture_body("adzuna_search")), settings=settings)
    db_exec("UPDATE budget SET utc_day = ?", "2000-01-01")
    assert calls_left(settings) == 1


def test_retries_spend_one_budget_call_per_attempt():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503, json={})

    with pytest.raises(GatewayError):
        rerun(handler)
    assert len(calls) == 3 and calls_left() == 22


def test_adzuna_429_locks_the_utc_day_across_a_reopen():
    seen = []
    with pytest.raises(GatewayError, match="adzuna.*limit"):
        rerun(serve({}, status=429, seen=seen))
    assert len(seen) == 1 and calls_left() == 0

    with pytest.raises(GatewayError, match="adzuna.*limit"):
        rerun(serve(fixture_body("adzuna_search"), seen=seen))  # a reopened gateway makes no call
    assert len(seen) == 1


# --- test fake ---

def test_fake_gateway_returns_canned_results_in_order():
    outcome = SourceOutcome(total=1, dropped=0, cache=CacheStatus.miss, fetched_at="2026-10-30T00:00:00Z", calls_left=None)
    first = FetchResult(postings=[], merged={}, sources={Source.adzuna: outcome}, failures={})
    second = FetchResult(postings=[], merged={}, sources={}, failures={Source.adzuna: "down"})

    async def go():
        async with FakeGateway([first, second]) as gw:
            return await gw.fetch(make_fetch()), await gw.fetch(make_fetch(page=2))

    assert asyncio.run(go()) == (first, second)
