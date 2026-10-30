import asyncio
import copy
import json
import logging
import sqlite3
from datetime import UTC, date, datetime, timedelta
from math import ceil
from pathlib import Path

import httpx
import langsmith as ls
import pytest
from unittest.mock import MagicMock

from talent_scout.gateway import http
from talent_scout.gateway import store as store_module
from talent_scout.gateway import usajobs
from talent_scout.gateway.adzuna import AdzunaClient
from talent_scout.gateway.gateway import make_gateway
from talent_scout.gateway.store import Store
from talent_scout.gateway.testing import FakeGateway
from talent_scout.gateway.types import BudgetExhausted, CacheStatus, Fetch, FetchResult, GatewayError, SourceOutcome, SourceRejected, SourceUnavailable
from talent_scout.gateway.usajobs import UsajobsClient
from talent_scout.kernel.testing import make_settings
from talent_scout.kernel.types import Salary, Source

FIXTURES = Path(__file__).parent / "fixtures" / "jobs"
APP_ID, APP_KEY = "test-app-id", "test-secret-key"
USAJOBS_HOST = "data.usajobs.gov"
TODAY = date(2026, 10, 30)  # the day the fixtures were recorded


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


def route(adzuna, usajobs=None):
    """Sends USAJOBS requests to `usajobs` and the rest to `adzuna`. USAJOBS defaults to down, so Adzuna tests see only Adzuna answer."""
    usajobs = usajobs or serve({}, status=503)
    return lambda request: (usajobs if request.url.host == USAJOBS_HOST else adzuna)(request)


def run_all(handler, *fetches, settings=None, usajobs=None):
    """Fetches in order through one open gateway."""
    async def go():
        async with make_gateway(settings or gateway_settings(), transport=httpx.MockTransport(route(handler, usajobs))) as gw:
            return [await gw.fetch(f) for f in fetches]

    return asyncio.run(go())


def run_fetch_keeping_db(handler, f=None, settings=None, usajobs=None):
    """One fetch against whatever gateway_db already holds, like a restarted process."""
    return run_all(handler, f or make_fetch(), settings=settings, usajobs=usajobs)[0]


def run_fetch(handler, f=None, settings=None, usajobs=None):
    # Starts from an empty gateway_db, so serving a different body for the same Fetch never meets an old L1 row.
    (settings or gateway_settings()).gateway_db.unlink(missing_ok=True)
    return run_fetch_keeping_db(handler, f, settings, usajobs)


def run_search(handler, f=None, client_cls=AdzunaClient):
    async def go():
        settings = gateway_settings()
        store = Store(settings)
        try:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await client_cls(client, settings, store).search(f or make_fetch())
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
def set_today(monkeypatch):
    """Pins the Gateway's clock, since USAJOBS close dates in the fixtures are real. Call the returned setter to move the day."""
    def setter(day=TODAY):
        monkeypatch.setattr(store_module, "today", lambda: day)

    setter()
    return setter


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
    run_fetch_keeping_db(serve(fixture_body("adzuna_search")), settings=settings)
    seen = []
    out = run_fetch_keeping_db(serve({}, seen=seen), settings=settings)
    assert seen == [] and out.sources[Source.adzuna].cache == CacheStatus.hit
    assert out.sources[Source.adzuna].calls_left == 0


def backdate(hours):
    db_exec("UPDATE l1 SET fetched_at = ?", (datetime.now(UTC) - timedelta(hours=hours)).isoformat())


def test_row_past_the_ttl_misses_and_is_overwritten():
    run_fetch_keeping_db(serve({"count": 0, "results": []}))
    backdate(25)
    seen = []
    out = run_fetch_keeping_db(serve(fixture_body("adzuna_search"), seen=seen))
    assert len(seen) == 1 and out.sources[Source.adzuna].cache == CacheStatus.miss
    # Overwritten, so the next identical Fetch is served from the refreshed row.
    assert run_fetch_keeping_db(serve({}, seen=seen)).sources[Source.adzuna].cache == CacheStatus.hit
    assert len(seen) == 1


def test_row_just_inside_the_ttl_is_still_a_hit():
    run_fetch_keeping_db(serve(fixture_body("adzuna_search")))
    backdate(23)
    assert run_fetch_keeping_db(serve({})).sources[Source.adzuna].cache == CacheStatus.hit


def test_stale_row_is_not_served_when_the_budget_has_run_out():
    settings = gateway_settings(adzuna_daily_limit=1)
    run_fetch_keeping_db(serve(fixture_body("adzuna_search")), settings=settings)
    backdate(25)
    db_exec("DELETE FROM l2_postings")  # L2 would otherwise answer for the stale row
    seen = []
    # With no other source the refusal surfaces as GatewayError; failures[adzuna] carries the same text.
    with pytest.raises(GatewayError, match="adzuna.*limit"):
        run_fetch_keeping_db(serve({}, seen=seen), settings=settings)
    assert seen == []


def test_row_that_no_longer_validates_is_a_miss():
    run_fetch_keeping_db(serve(fixture_body("adzuna_search")))
    db_exec("UPDATE l1 SET postings = ?", '[{"title": "old shape"}]')
    seen = []
    out = run_fetch_keeping_db(serve(fixture_body("adzuna_search"), seen=seen))
    assert len(seen) == 1 and out.sources[Source.adzuna].cache == CacheStatus.miss


@pytest.mark.parametrize("fetched_at", ["not a date", (datetime.now(UTC) + timedelta(days=1)).isoformat()])
def test_corrupt_or_future_fetched_at_is_a_miss(fetched_at):
    run_fetch(serve(fixture_body("adzuna_search")))
    db_exec("UPDATE l1 SET fetched_at = ?", fetched_at)
    seen = []
    out = run_fetch_keeping_db(serve(fixture_body("adzuna_search"), seen=seen))
    assert len(seen) == 1 and out.sources[Source.adzuna].cache == CacheStatus.miss


def test_concurrent_identical_fetches_share_one_call():
    seen = []

    async def go():
        async with make_gateway(gateway_settings(), transport=httpx.MockTransport(route(serve(fixture_body("adzuna_search"), seen=seen)))) as gw:
            return await asyncio.gather(gw.fetch(make_fetch()), gw.fetch(make_fetch()))

    a, b = asyncio.run(go())
    assert len(seen) == 1
    assert {a.sources[Source.adzuna].cache, b.sources[Source.adzuna].cache} == {CacheStatus.miss, CacheStatus.hit}


def test_empty_result_list_is_cached_but_failures_and_bad_bodies_are_not():
    seen = []
    first, second = run_all(serve({"count": 0, "results": []}, seen=seen), make_fetch(), make_fetch())
    assert second.sources[Source.adzuna].cache == CacheStatus.hit and len(seen) == 1
    assert second.postings == []

    db_exec("DELETE FROM l1")
    for handler in (serve({}, status=500), serve({"count": 3}), serve({}, status=429)):
        with pytest.raises(GatewayError):
            run_fetch_keeping_db(handler)
    assert db_exec("SELECT COUNT(*) FROM l1") == [(0,)]


def test_rows_are_committed_before_fetch_returns_and_hold_no_credentials():
    async def go():
        async with make_gateway(gateway_settings(), transport=httpx.MockTransport(route(serve(fixture_body("adzuna_search"))))) as gw:
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
    run_fetch_keeping_db(serve(fixture_body("adzuna_search")), settings=settings)
    db_exec("UPDATE budget SET utc_day = ?", "2000-01-01")
    assert calls_left(settings) == 1


def test_retries_spend_one_budget_call_per_attempt():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503, json={})

    with pytest.raises(GatewayError):
        run_fetch_keeping_db(handler)
    assert len(calls) == 3 and calls_left() == 22


def test_adzuna_429_locks_the_utc_day_across_a_reopen():
    seen = []
    with pytest.raises(GatewayError, match="adzuna.*limit"):
        run_fetch_keeping_db(serve({}, status=429, seen=seen))
    assert len(seen) == 1 and calls_left() == 0

    with pytest.raises(GatewayError, match="adzuna.*limit"):
        run_fetch_keeping_db(serve(fixture_body("adzuna_search"), seen=seen))  # a reopened gateway makes no call
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


# --- replay ---

def replay_settings(tmp_path):
    return gateway_settings(replay_cache=tmp_path / "replay.sqlite")


def replay_exec(tmp_path, sql, *args):
    """Raw SQL on the replay file through a second connection."""
    db = sqlite3.connect(tmp_path / "replay.sqlite")
    try:
        rows = db.execute(sql, args).fetchall()
        db.commit()
        return rows
    finally:
        db.close()


def test_recorded_answer_replays_past_its_ttl_with_no_http_call(tmp_path):
    s = replay_settings(tmp_path)
    recorded = run_fetch(serve(fixture_body("adzuna_search")), settings=s)
    replay_exec(tmp_path, "UPDATE jobs SET fetched_at = '2020-01-01T00:00:00+00:00'")
    seen = []
    out = run_fetch(serve({}, status=500, seen=seen), settings=s)  # a fresh gateway_db, so only the replay file can answer
    outcome = out.sources[Source.adzuna]
    assert seen == []
    assert outcome.cache == CacheStatus.replay and outcome.fetched_at == datetime(2020, 1, 1, tzinfo=UTC)
    assert out.postings == recorded.postings and outcome.total == 3200


def test_replay_miss_goes_live_and_is_written_as_served(tmp_path):
    s = replay_settings(tmp_path)
    assert run_fetch(serve(fixture_body("adzuna_search")), settings=s).sources[Source.adzuna].cache == CacheStatus.miss
    assert replay_exec(tmp_path, "SELECT source, total, dropped FROM jobs") == [("adzuna", 3200, 0)]


def test_budget_counters_stay_in_gateway_db_whatever_the_replay_path(tmp_path):
    s = replay_settings(tmp_path)
    live = run_fetch(serve(fixture_body("adzuna_search")), settings=s)
    assert live.sources[Source.adzuna].calls_left == s.adzuna_daily_limit - 1
    # A replayed answer spends nothing and reports the counter from gateway_db, not from the recording.
    replayed = run_fetch_keeping_db(serve({}, status=500), settings=s)
    assert replayed.sources[Source.adzuna].cache == CacheStatus.replay
    assert replayed.sources[Source.adzuna].calls_left == s.adzuna_daily_limit - 1
    assert calls_left(s) == s.adzuna_daily_limit - 1
    assert replay_exec(tmp_path, "SELECT name FROM sqlite_master WHERE name LIKE '%budget%'") == []


def test_unset_replay_cache_creates_no_replay_file(tmp_path):
    run_fetch(serve(fixture_body("adzuna_search")))
    assert [p.name for p in tmp_path.iterdir()] == [".cache"]


# --- tracing ---

def traced_fetch(handler, *fetches):
    """Fetches inside a parent run against a fake LangSmith client, returning the results and every call the client got."""
    client = MagicMock()

    async def go():
        async with make_gateway(gateway_settings(), transport=httpx.MockTransport(route(handler))) as gw:
            with ls.trace("run", "chain"):
                return [await gw.fetch(f) for f in fetches]

    with ls.tracing_context(enabled=True, client=client):
        out = asyncio.run(go())
    return out, client.method_calls


def gateway_updates(calls):
    return [c.kwargs for c in calls if c.kwargs.get("name") == "gateway:adzuna" and c[0] == "update_run"]


def test_each_source_call_is_a_child_run_with_summary_metadata():
    (first, _), calls = traced_fetch(serve(fixture_body("adzuna_search")), make_fetch(page=2), make_fetch(page=2))
    creates = [c.kwargs for c in calls if c.kwargs.get("name") == "gateway:adzuna" and c[0] == "create_run"]
    miss, hit = gateway_updates(calls)
    assert len(creates) == 2 and all(c["parent_run_id"] for c in creates)
    meta = {k: v for k, v in miss["extra"]["metadata"].items() if k != "ls_method"}
    assert meta == {"source": "adzuna", "page": 2, "cache": "miss", "calls_left": 24}
    assert hit["extra"]["metadata"]["cache"] == "hit"
    assert miss["outputs"] == {"count": 50, "dropped": 0, "total": 3200}


def test_trace_never_carries_postings_a_url_or_a_key():
    (out, _), calls = traced_fetch(serve(fixture_body("adzuna_search")), make_fetch(), make_fetch())
    sent = repr(calls)
    assert out.postings and "adzuna.com" not in sent and APP_KEY not in sent and APP_ID not in sent
    assert all(p.title not in sent for p in out.postings)


# --- USAJOBS mapping ---

def usajobs_items():
    return copy.deepcopy(fixture_body("usajobs_search")["SearchResult"]["SearchResultItems"])


def usajobs_page(items):
    return {"SearchResult": {"SearchResultCountAll": len(items), "SearchResultItems": items}}


def usajobs_item(item_id="759326100", details=None, **over):
    """One raw fixture item (the CIA Data Engineer unless told otherwise), with descriptor fields overridden."""
    item = next(i for i in usajobs_items() if i["MatchedObjectId"] == item_id)
    item["MatchedObjectDescriptor"].update(over)
    item["MatchedObjectDescriptor"]["UserArea"]["Details"].update(details or {})
    return item


def map_usajobs(*items, f=None):
    return run_search(serve(usajobs_page(list(items))), f, UsajobsClient)


def pay(code="PA", lo="100", hi="200"):
    return {"PositionRemuneration": [{"MinimumRange": lo, "MaximumRange": hi, "RateIntervalCode": code}]}


def test_usajobs_fixture_maps_description_url_and_pay():
    page = run_search(serve(fixture_body("usajobs_search")), client_cls=UsajobsClient)
    assert (len(page.postings), page.total, page.dropped) == (25, 65, 0)
    cia = page.postings[0]
    summary = usajobs_item()["MatchedObjectDescriptor"]["UserArea"]["Details"]["JobSummary"]
    assert cia.description.startswith(summary) and len(cia.description) <= 4000
    assert cia.url == "https://www.usajobs.gov/job/759326100"
    assert all(":443" not in p.url for p in page.postings)
    assert (cia.source, cia.source_id, cia.title, cia.company) == (Source.usajobs, "759326100", "Data Engineer", "Central Intelligence Agency")
    assert cia.salary == Salary(min=74584, max=156755, currency="USD", period="annual", predicted=False)
    assert (cia.posted_at, cia.closes_at, cia.domain) == (date(2026, 9, 1), date(2027, 1, 31), "it-jobs")
    assert cia.region == ("US", "District of Columbia", "Washington")


@pytest.mark.parametrize("code, period", [("PA", "annual"), ("PH", "hourly"), ("PD", "daily"), ("BW", "biweekly"), ("PM", "monthly")])
def test_usajobs_pay_codes_map_to_periods(code, period):
    assert map_usajobs(usajobs_item(**pay(code))).postings[0].salary.period == period


@pytest.mark.parametrize("code", ["SY", "PW", "FB", "ST", "WC"])
def test_usajobs_incomparable_pay_codes_give_no_salary(code):
    assert map_usajobs(usajobs_item(**pay(code))).postings[0].salary is None


@pytest.mark.parametrize("lo, hi, expected", [("200", "100", (100, 200)), ("0", "150", (None, 150)), ("100", "0", (100, None)), ("0", "0", None)])
def test_usajobs_salary_bounds(lo, hi, expected):
    salary = map_usajobs(usajobs_item(**pay("PA", lo, hi))).postings[0].salary
    assert (salary and (salary.min, salary.max)) == expected
    assert salary is None or salary.predicted is False


def test_usajobs_region_is_the_common_prefix_of_the_locations():
    page = map_usajobs(usajobs_item("852270300"), usajobs_item("890415500"), usajobs_item("889388600"))
    faa, virginia, mixed_states = (p.region for p in page.postings)
    assert faa == ("US",)  # 1,176 locations across the country
    assert virginia == ("US", "Virginia")  # Dahlgren and Fort Belvoir
    assert mixed_states == ("US",)  # Missouri and Virginia


def test_usajobs_region_for_no_locations_mixed_countries_and_overseas():
    cia = usajobs_item()["MatchedObjectDescriptor"]["PositionLocation"][0]
    berlin = {**cia, "CountryCode": "Germany", "CountrySubDivisionCode": "Berlin", "CityName": "Berlin"}
    page = map_usajobs(
        usajobs_item(PositionLocation=[]),
        usajobs_item(PositionLocation=[cia, berlin]),
        usajobs_item(PositionLocation=[berlin]),
    )
    assert [p.region for p in page.postings] == [("US",), ("US",), ("Germany", "Berlin", "Berlin")]


def test_usajobs_blank_description_and_bad_posted_at_are_drops_but_bad_closes_at_is_not():
    blank = usajobs_item("759326100", details={"JobSummary": "", "MajorDuties": []}, QualificationSummary="")
    bad_posted = usajobs_item("889388600", PublicationStartDate="soon")
    missing_posted = usajobs_item("888547100")
    del missing_posted["MatchedObjectDescriptor"]["PublicationStartDate"]
    bad_closes = usajobs_item("889350600", ApplicationCloseDate="whenever")
    page = map_usajobs(blank, bad_posted, missing_posted, bad_closes)
    assert page.dropped == 3
    assert [(p.source_id, p.closes_at) for p in page.postings] == [("889350600", None)]


@pytest.mark.parametrize(
    "series, domain",
    [
        ("2210", "it-jobs"),  # family 2200
        ("0801", "engineering-jobs"),  # family 0800
        ("0391", "it-jobs"),  # series override over the 0300 family
        ("0028", "scientific-qa-jobs"),  # override over a family that has no tag
        ("1102", None),  # override to no Domain over the 1100 family
        ("8999", "maintenance-jobs"),  # the one series whose family is not its first two digits
        ("7777", None),  # unknown series
    ],
)
def test_usajobs_domain_table(series, domain):
    assert map_usajobs(usajobs_item(JobCategory=[{"Name": "x", "Code": series}])).postings[0].domain == domain


def test_unknown_usajobs_series_is_logged_once(caplog):
    usajobs._domain.cache_clear()  # an earlier test may have logged this series already
    item = usajobs_item(JobCategory=[{"Name": "x", "Code": "7777"}])
    with caplog.at_level(logging.WARNING):
        map_usajobs(item, item)
    assert sum("7777" in r.getMessage() for r in caplog.records) == 1


# --- USAJOBS request and errors ---

def test_usajobs_request_for_a_located_search():
    seen = []
    f = make_fetch(location="Washington", radius_km=50, max_days_old=90, category="it-jobs", page=3)
    run_search(serve(fixture_body("usajobs_search"), seen=seen), f, UsajobsClient)
    req = seen[0]
    assert req.url.host == USAJOBS_HOST and req.url.path == "/api/Search"
    # DatePosted is capped at 60, Radius is miles rounded up, and the category is never sent.
    assert dict(req.url.params) == {
        "PositionTitle": "data engineer", "ResultsPerPage": "50", "Page": "3", "DatePosted": "60",
        "LocationName": "washington", "Radius": str(ceil(50 / 1.609)),
    }
    assert req.headers["Host"] == USAJOBS_HOST
    assert req.headers["User-Agent"] == "d" and req.headers["Authorization-Key"] == "c"


def test_usajobs_blank_location_omits_location_and_radius_and_short_windows_pass_through():
    seen = []
    run_search(serve(fixture_body("usajobs_search"), seen=seen), make_fetch(radius_km=25, max_days_old=10), UsajobsClient)
    q = dict(seen[0].url.params)
    assert q["DatePosted"] == "10" and "LocationName" not in q and "Radius" not in q


def test_usajobs_429_is_source_unavailable_with_no_lockout():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(429, json={})

    with pytest.raises(SourceUnavailable) as e:
        run_search(handler, client_cls=UsajobsClient)
    assert type(e.value) is SourceUnavailable and len(calls) == 1
    assert len(map_usajobs(usajobs_item()).postings) == 1  # the next call still goes out


def test_usajobs_body_without_search_result_is_source_unavailable():
    for body in ({}, {"SearchResult": {"SearchResultCountAll": 3}}, ["x"]):
        with pytest.raises(SourceUnavailable):
            run_search(serve(body), client_cls=UsajobsClient)


def test_usajobs_reports_no_calls_left():
    out = run_fetch(serve({"count": 0, "results": []}), usajobs=serve(fixture_body("usajobs_search")))
    assert out.sources[Source.usajobs].calls_left is None
    assert out.sources[Source.usajobs].total == 65


# --- fan-out ---

def empty_adzuna():
    return serve({"count": 0, "results": []})


def test_us_calls_both_sources_and_other_countries_call_adzuna_only():
    adzuna_seen, usajobs_seen = [], []
    us = run_fetch(
        serve(fixture_body("adzuna_search"), seen=adzuna_seen), usajobs=serve(fixture_body("usajobs_search"), seen=usajobs_seen)
    )
    assert set(us.sources) == {Source.adzuna, Source.usajobs} and us.failures == {}
    assert {p.source for p in us.postings} == {Source.adzuna, Source.usajobs}

    adzuna_seen.clear(), usajobs_seen.clear()
    gb = run_fetch(serve(fixture_body("adzuna_search"), seen=adzuna_seen), make_fetch(country="gb"), usajobs=serve({}, seen=usajobs_seen))
    assert set(gb.sources) == {Source.adzuna} and len(adzuna_seen) == 1 and usajobs_seen == []


def test_both_sources_are_in_flight_at_once():
    arrived, both = set(), asyncio.Event()

    def rendezvous(body):
        async def handler(request):
            arrived.add(request.url.host)
            if len(arrived) == 2:
                both.set()
            await asyncio.wait_for(both.wait(), 1)  # a sequential fan-out would time out here
            return httpx.Response(200, json=body)

        return handler

    out = run_fetch(rendezvous({"count": 0, "results": []}), usajobs=rendezvous(usajobs_page([])))
    assert set(out.sources) == {Source.adzuna, Source.usajobs}


def test_one_source_failing_still_returns_the_other():
    out = run_fetch(serve(fixture_body("adzuna_search")), usajobs=serve({}, status=500))
    assert set(out.sources) == {Source.adzuna} and set(out.failures) == {Source.usajobs} and out.postings

    out = run_fetch(serve({}, status=500), usajobs=serve(fixture_body("usajobs_search")))
    assert set(out.sources) == {Source.usajobs} and set(out.failures) == {Source.adzuna} and out.postings


def test_source_rejected_from_one_source_wins_over_a_result_from_the_other():
    with pytest.raises(SourceRejected) as e:
        run_fetch(serve(fixture_body("adzuna_search")), usajobs=serve({}, status=401))
    assert e.value.source == Source.usajobs

    with pytest.raises(SourceRejected) as e:
        run_fetch(serve({}, status=401), usajobs=serve(fixture_body("usajobs_search")))
    assert e.value.source == Source.adzuna


def test_navsea_offices_stay_apart_a_re_announced_ad_collapses_and_faa_pay_plans_stay_apart():
    out = run_fetch(empty_adzuna(), usajobs=serve(fixture_body("usajobs_search")))
    ids = {p.source_id for p in out.postings}
    # Same title, employer and pay, but each office writes its own duties, so these are different jobs.
    assert {"889483500", "889352000"} <= ids
    # The FAA pairs differ in pay.
    assert {"852270300", "852270000"} <= ids

    # A second hiring path for the same ad carries the same text, so it collapses.
    ad = usajobs_item("889483500")["MatchedObjectDescriptor"]
    twin = usajobs_item(
        "889352000", details={"MajorDuties": ad["UserArea"]["Details"]["MajorDuties"]}, QualificationSummary=ad["QualificationSummary"]
    )
    out = run_fetch(empty_adzuna(), usajobs=serve(usajobs_page([usajobs_item("889483500"), twin])))
    (kept,) = out.postings
    assert sorted([kept.source_id, *(k.split(":")[1] for k in out.merged[kept.key])]) == ["889352000", "889483500"]


# --- close dates and the L1 purge ---

OPEN_AFTER_NOV_3 = [i for i in usajobs_items() if i["MatchedObjectDescriptor"]["ApplicationCloseDate"][:10] >= "2026-11-03"]


def usajobs_rows():
    return db_exec("SELECT fetch FROM l1 WHERE source = 'usajobs' ORDER BY fetch")


def test_expired_postings_are_filtered_on_hits_and_fresh_responses_and_not_counted_as_dropped(set_today):
    handler, usajobs = empty_adzuna(), serve(fixture_body("usajobs_search"))
    first = run_fetch(handler, usajobs=usajobs)
    assert len(first.postings) + sum(len(v) for v in first.merged.values()) == 25  # nothing has closed on the recording day

    set_today(date(2026, 11, 3))
    hit = run_fetch_keeping_db(handler, usajobs=usajobs)
    fresh = run_fetch(handler, usajobs=usajobs)
    for out, cache in ((hit, CacheStatus.hit), (fresh, CacheStatus.miss)):
        outcome = out.sources[Source.usajobs]
        assert outcome.cache == cache and outcome.dropped == 0
        assert all(p.closes_at >= date(2026, 11, 3) for p in out.postings)
        assert len(out.postings) + sum(len(v) for v in out.merged.values()) == len(OPEN_AFTER_NOV_3) < 25


def test_purge_after_a_live_write_deletes_only_rows_whose_postings_have_all_closed(set_today):
    handler = empty_adzuna()
    closing = usajobs_item("889350600", ApplicationCloseDate="2026-10-31T23:59:59.9970")
    later = usajobs_item("889536100", ApplicationCloseDate="2027-01-01T23:59:59.9970")
    all_closed, mixed, all_open = (make_fetch(page=n) for n in (1, 2, 3))

    run_fetch(handler, all_closed, usajobs=serve(usajobs_page([closing])))
    run_fetch_keeping_db(handler, mixed, usajobs=serve(usajobs_page([closing, later])))
    assert len(usajobs_rows()) == 2  # still open on the day they were written

    set_today(date(2026, 11, 1))
    run_fetch_keeping_db(handler, all_open, usajobs=serve(usajobs_page([later])))
    assert usajobs_rows() == [(mixed.model_dump_json(),), (all_open.model_dump_json(),)]


def test_replay_row_skips_the_close_date_filter_and_the_purge(set_today, tmp_path):
    s = replay_settings(tmp_path)
    usajobs = serve(fixture_body("usajobs_search"))
    run_fetch(empty_adzuna(), settings=s, usajobs=usajobs)
    db_exec("UPDATE l1 SET expires_at = '2026-10-01'")  # a row that a purge would delete

    set_today(date(2026, 11, 3))
    out = run_fetch_keeping_db(empty_adzuna(), settings=s, usajobs=serve({}, status=500))
    assert out.sources[Source.usajobs].cache == CacheStatus.replay
    assert len(out.postings) + sum(len(v) for v in out.merged.values()) == 25  # closed Postings included
    assert len(usajobs_rows()) == 1


# --- L2 store ---

def adzuna_batch(n, start=0, **over):
    """n distinct Adzuna results with distinct employers, so coalesce keeps every one of them."""
    return [
        raw_result(id=f"{i:04d}", company={"display_name": f"Co {i}"}, **{"title": "Data Engineer", **over})
        for i in range(start, start + n)
    ]


def adzuna_page(results, count=None):
    return {"count": len(results) if count is None else count, "results": results}


def l2_rows():
    return db_exec("SELECT key, via, last_seen_at FROM l2_postings ORDER BY key")


def ago(**delta):
    return (datetime.now(UTC) - timedelta(**delta)).isoformat()


def store_page(results, **fetch):
    """Fills L2 through a live call on an empty gateway_db."""
    return run_fetch(serve(adzuna_page(results)), make_fetch(**fetch))


GB = dict(country="gb")


def test_every_live_adzuna_page_is_written_to_l2_before_coalesce_and_the_newest_version_wins():
    first, second = make_fetch(page=2), make_fetch(page=3)
    # Same title, employer, text and pay, so coalesce collapses these two.
    out = run_fetch(serve(adzuna_page([raw_result(id="1"), raw_result(id="2")])), first)
    assert len(out.postings) == 1
    assert [r[0] for r in l2_rows()] == ["adzuna:1", "adzuna:2"]

    stamp = ago(days=2)
    db_exec("UPDATE l2_postings SET last_seen_at = ?", stamp)
    run_fetch_keeping_db(serve(adzuna_page([raw_result(id="1", title="Data Engineer II")])), second)
    (_, via1, seen1), (_, via2, seen2) = l2_rows()
    assert (via1, via2) == (second.model_dump_json(), first.model_dump_json())
    assert seen1 > ago(days=1) and seen2 == stamp
    assert json.loads(db_exec("SELECT posting FROM l2_postings WHERE key = 'adzuna:1'")[0][0])["title"] == "Data Engineer II"


SENIOR, PLAIN = "Senior Data Engineer", "Data Engineer"


@pytest.mark.parametrize(
    "via_title, via_location, stored_title, new_title, new_location, reused",
    [
        ("data engineer", "london", SENIOR, "senior data engineer", "london", True),
        ("senior data engineer", "london", SENIOR, "data engineer", "london", False),
        ("data engineer", "camden", PLAIN, "data engineer", "london", False),
        ("data engineer", "", PLAIN, "data engineer", "camden", True),
    ],
    ids=["narrower title", "broader title", "other location", "country-wide"],
)
def test_reuse_table(via_title, via_location, stored_title, new_title, new_location, reused):
    place = {"display_name": "Camden, London", "area": ["GB", "London", "Camden"]}
    via = dict(title=via_title, location=via_location, **GB)
    run_fetch(serve(adzuna_page(adzuna_batch(50, 0, title=stored_title, location=place))), make_fetch(**via))
    # Page 2 holds plain titles, so the first row can show that only the senior jobs are reused.
    run_fetch_keeping_db(serve(adzuna_page(adzuna_batch(50, 50, location=place))), make_fetch(page=2, **via))

    seen = []
    out = run_fetch_keeping_db(serve(adzuna_page([]), seen=seen), make_fetch(title=new_title, location=new_location, **GB))
    outcome = out.sources[Source.adzuna]
    if reused:
        assert seen == [] and outcome.cache == CacheStatus.store
        assert (outcome.total, len(out.postings)) == ((50 if "senior" in new_title else 100), 50)
        assert all(set(new_title.split()) <= set(p.title.lower().split()) for p in out.postings)
    else:
        assert len(seen) == 1 and outcome.cache == CacheStatus.miss


@pytest.mark.parametrize(
    "odd",
    [
        dict(title="Data Analyst"),
        dict(created="2026-08-01T10:00:00Z"),  # 90 days before the pinned day, past max_days_old
        dict(category={"tag": "sales-jobs"}),
        dict(location={"display_name": "Soho", "area": ["GB", "London", "Soho"]}),
    ],
    ids=["title words", "age", "domain", "region"],
)
def test_l2_leaves_out_postings_that_adzuna_would_not_have_returned(odd):
    base = dict(location={"display_name": "Camden", "area": ["GB", "London", "Camden"]}, category={"tag": "it-jobs"})
    results = adzuna_batch(50, 0, **base) + adzuna_batch(1, 900, **{**base, **odd})
    run_fetch(serve(adzuna_page(results)), make_fetch(max_days_old=90, **GB))  # a country-wide, uncategorised Fetch

    out = run_fetch_keeping_db(serve({}, status=500), make_fetch(location="camden", category="it-jobs", **GB))
    assert out.sources[Source.adzuna].cache == CacheStatus.store and out.failures == {}
    assert out.sources[Source.adzuna].total == 50 and "adzuna:0900" not in {p.key for p in out.postings}


def test_page_n_is_served_only_when_its_slice_is_full():
    store_page(adzuna_batch(50), **GB)
    run_fetch_keeping_db(serve(adzuna_page(adzuna_batch(25, 50))), make_fetch(page=2, **GB))
    seen = []
    first, second = run_all(
        serve(adzuna_page([]), seen=seen), make_fetch(max_days_old=45, **GB), make_fetch(max_days_old=45, page=2, **GB)
    )
    a, b = first.sources[Source.adzuna], second.sources[Source.adzuna]
    assert (a.cache, a.total, len(first.postings)) == (CacheStatus.store, 75, 50)
    assert b.cache == CacheStatus.miss and len(seen) == 1  # 25 rows are a short page 2


def test_reading_l2_before_the_call_spends_no_budget():
    s = gateway_settings(adzuna_daily_limit=1)
    run_fetch(serve(adzuna_page(adzuna_batch(50))), make_fetch(**GB), settings=s)  # the day's only call
    seen = []
    out = run_fetch_keeping_db(serve({}, status=500, seen=seen), make_fetch(max_days_old=45, **GB), settings=s)
    assert seen == [] and out.sources[Source.adzuna].cache == CacheStatus.store
    assert out.sources[Source.adzuna].calls_left == 0 and calls_left(s) == 0


def test_serving_from_l2_leaves_last_seen_alone_and_reports_the_oldest():
    store_page(adzuna_batch(50), **GB)
    oldest, newer = ago(days=3), ago(days=2)
    db_exec("UPDATE l2_postings SET last_seen_at = ?", newer)
    db_exec("UPDATE l2_postings SET last_seen_at = ? WHERE key = 'adzuna:0001'", oldest)

    out = run_fetch_keeping_db(serve({}, status=500), make_fetch(max_days_old=45, **GB))
    o = out.sources[Source.adzuna]
    assert (o.cache, o.total, o.dropped, o.calls_left) == (CacheStatus.store, 50, 0, 24)
    assert o.fetched_at == datetime.fromisoformat(oldest)
    assert {r[2] for r in l2_rows()} == {oldest, newer}


@pytest.mark.parametrize("status", [500, 429])
def test_failed_live_call_falls_back_to_l2s_partial_page_and_still_reports_the_failure(status):
    store_page(adzuna_batch(10))
    out = run_fetch_keeping_db(serve({}, status=status), make_fetch(max_days_old=45), usajobs=serve(usajobs_page([])))
    o = out.sources[Source.adzuna]
    assert (o.cache, o.total, o.dropped, len(out.postings)) == (CacheStatus.store, 10, 0, 10)
    assert set(out.failures) == {Source.adzuna} and set(out.sources) == {Source.adzuna, Source.usajobs}


def test_failed_live_call_with_no_l2_matches_only_reports_the_failure():
    store_page(adzuna_batch(10))
    out = run_fetch_keeping_db(serve({}, status=500), make_fetch(title="nurse"), usajobs=serve(usajobs_page([])))
    assert set(out.sources) == {Source.usajobs} and set(out.failures) == {Source.adzuna}


def test_a_rejected_call_is_not_covered_for_by_l2():
    store_page(adzuna_batch(10))
    with pytest.raises(SourceRejected):
        run_fetch_keeping_db(serve({}, status=401), make_fetch(max_days_old=45))


def test_l2_answer_is_not_written_to_l1_and_is_recorded_in_the_replay_file(tmp_path):
    s = replay_settings(tmp_path)
    run_fetch(serve(adzuna_page(adzuna_batch(50))), make_fetch(**GB), settings=s)
    f = make_fetch(max_days_old=45, **GB)
    out = run_fetch_keeping_db(serve({}, status=500), f, settings=s)
    assert out.sources[Source.adzuna].cache == CacheStatus.store
    assert db_exec("SELECT COUNT(*) FROM l1 WHERE fetch = ?", f.model_dump_json()) == [(0,)]
    assert replay_exec(tmp_path, "SELECT total FROM jobs WHERE fetch = ?", f.model_dump_json()) == [(50,)]


def test_replay_hit_returns_before_l2(tmp_path):
    s = replay_settings(tmp_path)
    f = make_fetch(**GB)
    run_fetch(serve(adzuna_page(adzuna_batch(50), count=3200)), f, settings=s)
    db_exec("DELETE FROM l1")  # leaves L2 as the only other thing that could answer
    o = run_fetch_keeping_db(serve({}, status=500), f, settings=s).sources[Source.adzuna]
    assert (o.cache, o.total) == (CacheStatus.replay, 3200)


def test_usajobs_postings_are_never_stored_in_l2():
    out = run_fetch(serve(adzuna_page(adzuna_batch(3))), usajobs=serve(fixture_body("usajobs_search")))
    assert {p.source for p in out.postings} == {Source.adzuna, Source.usajobs}
    assert {key.split(":")[0] for key, *_ in l2_rows()} == {"adzuna"}


def test_l2_row_that_no_longer_validates_is_skipped():
    store_page(adzuna_batch(50))
    db_exec("UPDATE l2_postings SET posting = ? WHERE key = 'adzuna:0007'", '{"title": "old shape"}')
    out = run_fetch_keeping_db(serve({}, status=500), make_fetch(max_days_old=45), usajobs=serve(usajobs_page([])))
    assert out.sources[Source.adzuna].total == 49 and Source.adzuna in out.failures  # a short page, so the call was tried


def test_l2_rows_past_the_fresh_window_are_hidden_on_read_and_deleted_after_the_next_live_write():
    store_page(adzuna_batch(50), **GB)
    db_exec("UPDATE l2_postings SET last_seen_at = ?", ago(days=8))
    seen = []
    out = run_fetch_keeping_db(serve(adzuna_page(adzuna_batch(3, 900)), seen=seen), make_fetch(max_days_old=45, **GB))
    assert len(seen) == 1 and out.sources[Source.adzuna].cache == CacheStatus.miss  # 50 stale rows would have filled the page
    assert [key for key, *_ in l2_rows()] == ["adzuna:0900", "adzuna:0901", "adzuna:0902"]
