import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from talent_scout.clients import web
from talent_scout.kernel.testing import make_settings

ALICE, BOB = "alice@example.com", "bob@example.com"


def make_client(tmp_path, delay=0.02):
    settings = make_settings(
        demo=True, demo_delay=delay, runs_db=tmp_path / "runs.sqlite", runs_dir=tmp_path / "runs",
        web_origin="https://scout.example", render_external_hostname="api.example",
        sign_in=True, google_client_id="id", google_client_secret="secret", allowed_emails=[ALICE.upper(), BOB],
    )
    return TestClient(web.make_app(settings), base_url="https://api.example")


@pytest.fixture
def hosted(tmp_path):
    with make_client(tmp_path) as client:
        yield client


def fake_google(client, **profile):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/token":
            return httpx.Response(200, json={"access_token": "t"})
        return httpx.Response(200, json=profile)

    client.app.state.google_transport = httpx.MockTransport(handler)


def sign_in(client, email, *, verified=True, sub=None, state=None) -> str:
    """Walk the whole flow against a fake Google and return where the callback sent the browser."""
    client.cookies.clear()
    fake_google(client, sub=sub or email, email=email, email_verified=verified)
    begin = client.get("/api/auth/google", follow_redirects=False)
    sent = parse_qs(urlparse(begin.headers["location"]).query)["state"][0]
    done = client.get("/api/auth/google/callback", params={"code": "c", "state": state or sent}, follow_redirects=False)
    return done.headers["location"]


def test_signed_out_sees_only_meta_and_the_sign_in_routes(hosted):
    assert hosted.get("/api/meta").json()["sign_in"] is True
    for path in ("/api/me", "/api/runs", "/api/customers", "/api/runs/abc"):
        refused = hosted.get(path)
        assert refused.status_code == 401 and refused.json()["code"] == "signed_out"
    begin = hosted.get("/api/auth/google", follow_redirects=False)
    query = parse_qs(urlparse(begin.headers["location"]).query)
    assert begin.headers["location"].startswith("https://accounts.google.com/")
    assert query["redirect_uri"] == ["https://scout.example/api/auth/google/callback"] and query["scope"] == ["openid email"]
    assert "__Host-state" in begin.headers["set-cookie"] and "Secure" in begin.headers["set-cookie"]


def test_an_allowed_email_signs_in_and_out(hosted):
    assert sign_in(hosted, ALICE) == "/"
    assert hosted.get("/api/me").json()["email"] == ALICE
    cookie = hosted.cookies["__Host-session"]
    assert "HttpOnly" in hosted.post("/api/auth/logout").headers["set-cookie"]
    assert hosted.get("/api/me").status_code == 401
    # The token is dead on the server too, not merely forgotten by the browser.
    hosted.cookies.set("__Host-session", cookie, domain="api.example")
    assert hosted.get("/api/me").status_code == 401


def test_only_the_hash_of_a_token_is_stored(hosted):
    sign_in(hosted, ALICE)
    rows = hosted.portal.call(hosted.app.state.controller.accounts._run, "SELECT token_hash FROM sessions")
    assert len(rows) == 1 and hosted.cookies["__Host-session"] not in rows[0]["token_hash"]


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"email": "mallory@example.com"}, "not_allowed"),
        ({"email": ALICE, "verified": False}, "unverified_email"),
        ({"email": ALICE, "state": "forged"}, "bad_state"),
    ],
)
def test_a_failed_sign_in_redirects_with_a_code_and_sets_no_session(hosted, kwargs, code):
    assert sign_in(hosted, **kwargs) == f"/?signin={code}"
    assert hosted.get("/api/me").status_code == 401


def test_google_failing_is_a_code_too(hosted):
    hosted.cookies.clear()
    hosted.app.state.google_transport = httpx.MockTransport(lambda request: httpx.Response(500))
    state = parse_qs(urlparse(hosted.get("/api/auth/google", follow_redirects=False).headers["location"]).query)["state"][0]
    done = hosted.get("/api/auth/google/callback", params={"code": "c", "state": state}, follow_redirects=False)
    assert done.headers["location"] == "/?signin=google_failed"
    # No state cookie at all is a bad state before it is anything else.
    hosted.cookies.clear()
    assert hosted.get("/api/auth/google/callback", params={"code": "c"}, follow_redirects=False).headers["location"] == "/?signin=bad_state"


def test_a_session_expires_after_its_30_days(hosted):
    sign_in(hosted, ALICE)
    hosted.portal.call(hosted.app.state.controller.accounts._run, "UPDATE sessions SET expires_at = ?", ("2000-01-01T00:00:00+00:00",))
    assert hosted.get("/api/me").json()["code"] == "signed_out"


def test_removal_mid_session_ends_it_but_keeps_the_data(tmp_path):
    with make_client(tmp_path) as client:
        sign_in(client, BOB)
        customer = client.post("/api/customers", json={"name": "Acme"}).json()
        client.app.state.settings.allowed_emails.remove(BOB)
        assert client.get("/api/customers").status_code == 401
        sessions = client.portal.call(client.app.state.controller.accounts._run, "SELECT * FROM sessions")
        assert sessions == []
        # Added back, the same CSM finds everything where they left it.
        client.app.state.settings.allowed_emails.append(BOB)
        sign_in(client, BOB)
        assert [c["id"] for c in client.get("/api/customers").json()] == [customer["id"]]


def test_writes_keep_the_origin_check(hosted):
    sign_in(hosted, ALICE)
    refused = hosted.post("/api/customers", json={"name": "x"}, headers={"Origin": "http://evil.example"})
    assert refused.status_code == 403 and refused.json()["code"] == "foreign_origin"
    assert hosted.post("/api/auth/logout", headers={"Origin": "http://evil.example"}).status_code == 403


def test_without_sign_in_the_app_is_login_free(tmp_path):
    settings = make_settings(demo=True, runs_db=tmp_path / "runs.sqlite", runs_dir=tmp_path / "runs")
    with TestClient(web.make_app(settings), base_url="http://127.0.0.1") as client:
        assert client.get("/api/meta").json()["sign_in"] is False
        assert client.get("/api/me").json()["email"] == "local@localhost"
        assert [c["name"] for c in client.get("/api/customers").json()] == ["Local"]


def customer_of(client, name="Acme") -> str:
    return client.post("/api/customers", json={"name": name}).json()["id"]


def test_customers_are_added_found_renamed_and_private(hosted):
    sign_in(hosted, ALICE)
    acme = hosted.post("/api/customers", json={"name": "  Acme  ", "note": "Berlin, data roles"})
    assert acme.status_code == 201 and acme.json()["name"] == "Acme"
    twin = hosted.post("/api/customers", json={"name": "Acme"}).json()  # names may repeat
    listed = hosted.get("/api/customers").json()
    assert {c["id"] for c in listed} == {acme.json()["id"], twin["id"]}
    assert {c["note"] for c in listed} == {"Berlin, data roles", None}

    patched = hosted.patch(f"/api/customers/{twin['id']}", json={"name": "Globex", "note": "Paris"}).json()
    assert (patched["name"], patched["note"]) == ("Globex", "Paris")
    cleared = hosted.patch(f"/api/customers/{twin['id']}", json={"note": ""}).json()
    assert (cleared["name"], cleared["note"]) == ("Globex", None)

    sign_in(hosted, BOB)
    assert hosted.get("/api/customers").json() == []
    for call in (hosted.get, lambda p: hosted.patch(p, json={"name": "x"}), hosted.delete):
        assert call(f"/api/customers/{twin['id']}").status_code == 404


@pytest.mark.parametrize("body", [{"name": " "}, {}, {"name": "x" * 101}, {"name": "x", "note": "n" * 201}])
def test_a_blank_or_overlong_customer_field_is_a_422(hosted, body):
    sign_in(hosted, ALICE)
    assert hosted.post("/api/customers", json=body).status_code == 422
    acme = customer_of(hosted)
    assert hosted.patch(f"/api/customers/{acme}", json={"name": " "}).status_code == 422


def start(client, customer_id, text="Data Engineer"):
    return client.post("/api/runs", json={"request_text": text, "customer_id": customer_id})


def wait_idle(client, thread_id):
    for _ in range(200):
        detail = client.get(f"/api/runs/{thread_id}").json()
        if detail["live_from"] is None:
            return detail
        time.sleep(0.02)
    raise AssertionError("Run never went idle")


def test_a_run_starts_inside_a_customer_and_only_its_csm_sees_it(hosted):
    sign_in(hosted, ALICE)
    acme = customer_of(hosted)
    assert hosted.post("/api/runs", json={"request_text": "x"}).status_code == 422
    thread_id = start(hosted, acme).json()["thread_id"]
    wait_idle(hosted, thread_id)
    assert [r["thread_id"] for r in hosted.get(f"/api/runs?customer_id={acme}").json()] == [thread_id]
    assert hosted.get(f"/api/runs?customer_id={customer_of(hosted, 'Other')}").json() == []

    sign_in(hosted, BOB)
    assert start(hosted, acme).status_code == 404  # another CSM's Customer
    assert hosted.get("/api/runs").json() == []
    paths = [
        ("get", f"/api/runs/{thread_id}"), ("get", f"/api/runs/{thread_id}/events"), ("get", f"/api/runs/{thread_id}/brief.md"),
        ("post", f"/api/runs/{thread_id}/resume"), ("post", f"/api/runs/{thread_id}/cancel"), ("delete", f"/api/runs/{thread_id}"),
    ]
    for method, path in paths:
        refused = getattr(hosted, method)(path)
        assert refused.status_code == 404 and refused.json()["code"] == "not_found", path

    sign_in(hosted, ALICE)
    assert hosted.get(f"/api/runs/{thread_id}").status_code == 200  # still there, nothing deleted by Bob


def test_two_tabs_of_one_csm_attach_to_one_run(tmp_path):
    with make_client(tmp_path) as client:
        sign_in(client, ALICE)
        thread_id = start(client, customer_of(client)).json()["thread_id"]
        assert client.get(f"/api/runs/{thread_id}").json()["live_from"] == 0
        assert client.get(f"/api/runs/{thread_id}").json()["live_from"] == 0


def test_a_finished_run_is_deleted_with_its_files_and_a_live_one_is_refused(tmp_path):
    with make_client(tmp_path, delay=0.3) as client:
        sign_in(client, ALICE)
        thread_id = start(client, customer_of(client)).json()["thread_id"]
        live = client.delete(f"/api/runs/{thread_id}")
        assert live.status_code == 409 and live.json()["code"] == "run_live"
        wait_idle(client, thread_id)
        assert client.delete(f"/api/runs/{thread_id}").status_code == 204
        assert client.get(f"/api/runs/{thread_id}").status_code == 404
        assert client.get("/api/runs").json() == []


def test_deleting_a_customer_takes_its_runs_and_a_repeat_after_an_interruption_finishes(hosted, monkeypatch):
    sign_in(hosted, ALICE)
    acme, other = customer_of(hosted), customer_of(hosted, "Other")
    first, second = (start(hosted, acme).json()["thread_id"] for _ in range(2))
    kept = start(hosted, other).json()["thread_id"]
    for thread_id in (first, second, kept):
        wait_idle(hosted, thread_id)

    controller = hosted.app.state.controller
    real = controller.delete_run
    calls = []

    async def interrupted(thread_id):
        calls.append(thread_id)
        if len(calls) == 2:
            raise RuntimeError("process died")
        await real(thread_id)

    monkeypatch.setattr(controller, "delete_run", interrupted)
    with pytest.raises(RuntimeError):
        hosted.delete(f"/api/customers/{acme}")
    # One Run is gone, the Customer is still there, and trying again finishes the job.
    assert hosted.get(f"/api/customers/{acme}").status_code == 200
    monkeypatch.setattr(controller, "delete_run", real)
    assert hosted.delete(f"/api/customers/{acme}").status_code == 204
    assert hosted.get(f"/api/customers/{acme}").status_code == 404
    assert [r["thread_id"] for r in hosted.get("/api/runs").json()] == [kept]


def test_a_customer_with_a_live_run_cannot_be_deleted(tmp_path):
    with make_client(tmp_path, delay=0.3) as client:
        sign_in(client, ALICE)
        acme = customer_of(client)
        start(client, acme)
        refused = client.delete(f"/api/customers/{acme}")
        assert refused.status_code == 409 and refused.json()["code"] == "run_live"
