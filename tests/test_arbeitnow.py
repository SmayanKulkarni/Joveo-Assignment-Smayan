import asyncio
import copy
import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from talent_scout.gateway import arbeitnow, http
from talent_scout.gateway import store as store_module
from talent_scout.gateway.gateway import make_gateway
from talent_scout.gateway.store import Store
from talent_scout.gateway.types import Fetch, SourceUnavailable
from talent_scout.kernel.testing import make_settings
from talent_scout.kernel.types import Source

PAGE = json.loads((Path(__file__).parent / "fixtures" / "jobs" / "arbeitnow_page.json").read_text(encoding="utf-8"))["body"]
SETTINGS = dict(adzuna_app_id="a", ADZUNA_API_KEY="b")


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(http, "_DELAYS", (0, 0))
    monkeypatch.setattr(arbeitnow, "PAGE_PAUSE", 0)
    monkeypatch.setattr(store_module, "today", lambda: date(2026, 11, 2))


def fetch_for(**over) -> Fetch:
    base = dict(title="data engineer", country="de", location="", radius_km=0, max_days_old=30, category=None)
    return Fetch(**{**base, **over})


def serving(pages, seen=None):
    """Page N gets pages[N-1], and a page past the list is the empty one that ends a walk. An int is a status to answer with."""
    def handler(request):
        n = int(request.url.params["page"])
        if seen is not None:
            seen.append(n)
        body = pages[n - 1] if n <= len(pages) else {"data": []}
        return httpx.Response(body, json={}) if isinstance(body, int) else httpx.Response(200, json=body)

    return handler


def run(handler, *fetches, gather=False):
    async def go():
        async with make_gateway(make_settings(**SETTINGS), transport=httpx.MockTransport(handler)) as gw:
            calls = [gw.fetch(f, Source.arbeitnow) for f in fetches]
            if gather:
                return await asyncio.gather(*calls, return_exceptions=True)
            return [await c for c in calls]

    return asyncio.run(go())


def engineers():
    """The recorded page with every job retitled, so the title filter keeps them all."""
    return {**PAGE, "data": [{**r, "title": "Data Engineer"} for r in PAGE["data"]]}


def snapshot():
    store = Store(make_settings(**SETTINGS))
    try:
        cached = store.get_l1(Source.arbeitnow, "snapshot")
    finally:
        store.close()
    return cached and cached[0]


def mapped():
    return [arbeitnow._map(raw) for raw in PAGE["data"]]


def raw(**over):
    return copy.deepcopy(PAGE["data"][0]) | over


def test_a_posting_maps_with_no_pay_close_date_or_domain_and_plain_text():
    p = next(p for p in mapped() if p.location.startswith("Berlin, Berlin"))

    assert (p.salary, p.closes_at, p.domain, p.remote) == (None, None, None, False)
    assert p.region == ("Deutschland", "Berlin")  # Adzuna's root name for Germany, then the city
    assert "<" not in p.description and p.url.startswith("https://www.arbeitnow.com/")


def test_a_long_description_is_cut_at_4000_characters():
    p = arbeitnow._map(raw(description="<p>" + "word " * 2000 + "</p>"))

    assert len(p.description) == arbeitnow.MAX_DESCRIPTION


def test_remote_comes_from_the_flag_the_location_or_a_tag_and_gets_the_remote_region():
    flagged = arbeitnow._map(raw(remote=True, location="Munich"))
    located = arbeitnow._map(raw(remote=False, location="Berlin/Remote"))
    tagged = arbeitnow._map(raw(remote=False, location="Hamburg", tags=["Remote"]))
    plain = arbeitnow._map(raw(remote=False, location="Hamburg", tags=["Sales"]))

    assert all(p.remote and p.region == ("Remote",) for p in (flagged, located, tagged))
    assert not plain.remote and plain.region == ("Deutschland", "Hamburg")


def test_a_blank_location_falls_back_to_the_countrys_name():
    p = arbeitnow._map(raw(location=" ", remote=False, tags=[]))

    assert (p.location, p.region) == ("Deutschland", ("Deutschland",))


def test_a_posting_with_no_description_is_dropped_and_counted():
    (out,) = run(serving([{"data": [raw(description="<p> </p>")]}]), fetch_for())

    assert out.postings == [] and out.sources[Source.arbeitnow].dropped == 1


def test_any_country_gets_its_own_postings_and_every_remote_one():
    de, us = run(serving([engineers()]), fetch_for(), fetch_for(country="us"))

    assert {p.region[0] for p in de.postings} == {"Deutschland", "Remote"}
    assert {p.region for p in us.postings} == {("Remote",)}  # nothing local to a country the feed doesn't cover
    assert de.sources[Source.arbeitnow].calls_left is None


def test_title_location_and_age_filter_locally_and_the_place_leaves_remote_alone():
    berlin, london, nothing = run(
        serving([engineers()]),
        fetch_for(location="berlin"),
        fetch_for(country="gb", location="london"),
        fetch_for(title="zzzz"),
    )

    assert {p.region[:2] for p in berlin.postings if not p.remote} == {("Deutschland", "Berlin")}
    assert any(p.remote for p in berlin.postings)
    assert {p.region[0] for p in london.postings} == {"UK", "Remote"}
    assert nothing.postings == [] and nothing.sources[Source.arbeitnow].total == 0


def test_a_posting_older_than_max_days_old_is_filtered_out(monkeypatch):
    monkeypatch.setattr(store_module, "today", lambda: date(2026, 11, 20))

    (stale,) = run(serving([engineers()]), fetch_for(max_days_old=7))

    assert stale.postings == []


def test_results_come_newest_first_in_pages_of_50():
    raws = [raw(slug=f"s{i}", title="Data Engineer", company_name=f"Co {i}", created_at=1_793_500_000 + (i % 7) * 86_400, remote=False, location="Berlin", tags=[]) for i in range(120)]

    first, third = run(serving([{"data": raws}]), fetch_for(), fetch_for(page=3))

    dates = [p.posted_at for p in first.postings]
    assert dates == sorted(dates, reverse=True)
    assert (len(first.postings), len(third.postings), first.sources[Source.arbeitnow].total) == (50, 20, 120)


def test_the_walk_runs_once_and_a_posting_repeated_across_pages_counts_once():
    seen = []
    repeat = {"data": [PAGE["data"][0]]}

    run(serving([PAGE, repeat], seen), fetch_for(), fetch_for(location="berlin"), fetch_for(country="nl"))

    assert seen == [1, 2, 3]  # two pages, then the empty one that ends the walk
    assert snapshot().total == len(PAGE["data"])


def test_a_failed_walk_stores_no_snapshot_and_is_remembered_for_the_rest_of_the_run():
    seen = []

    async def go():
        async with make_gateway(make_settings(**SETTINGS), transport=httpx.MockTransport(serving([PAGE, 429], seen))) as gw:
            together = await asyncio.gather(
                gw.fetch(fetch_for(), Source.arbeitnow), gw.fetch(fetch_for(location="berlin"), Source.arbeitnow), return_exceptions=True
            )
            later = await asyncio.gather(gw.fetch(fetch_for(title="b"), Source.arbeitnow), return_exceptions=True)
            return [*together, *later]

    outcomes = asyncio.run(go())

    assert all(isinstance(o, SourceUnavailable) for o in outcomes)
    assert seen == [1, 2]  # no second walk after the 429, not even for the call that queued behind it
    assert snapshot() is None


def test_a_refusal_from_the_feed_is_a_source_failure_and_not_a_stop():
    (outcome,) = run(serving([403]), fetch_for(), gather=True)

    assert isinstance(outcome, SourceUnavailable)
