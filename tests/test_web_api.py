import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from talent_scout.clients import web
from talent_scout.kernel.llm import BalanceTooLow
from talent_scout.kernel.testing import make_settings
from talent_scout.runtime.guard import RunLocked
from talent_scout.runtime.graph import OWNERS

FOREIGN = {"Origin": "http://evil.example"}


@pytest.fixture
def client(tmp_path):
    settings = make_settings(demo=True, demo_delay=0.02, runs_db=tmp_path / "runs.sqlite", runs_dir=tmp_path / "runs")
    # The Host guard refuses TestClient's default "testserver", so the loopback base URL is required.
    with TestClient(web.make_app(settings), base_url="http://127.0.0.1") as client:
        yield client


def start(client, text="Data Engineer") -> str:
    response = client.post("/api/runs", json={"request_text": text, "focus": ["skills"]})
    assert response.status_code == 201
    return response.json()["thread_id"]


def wait_for(client, thread_id, status):
    for _ in range(200):
        detail = client.get(f"/api/runs/{thread_id}").json()
        if detail["record"]["status"] == status and detail["live_from"] is None:
            return detail
        time.sleep(0.02)
    raise AssertionError(f"Run never reached {status}")


def sse(response) -> list[dict]:
    return [json.loads(line.removeprefix("data:")) for line in response.text.splitlines() if line.startswith("data:")]


def test_meta_gives_the_graph_in_owner_order(client):
    meta = client.get("/api/meta").json()
    assert [n["id"] for n in meta["graph"]["nodes"]] == [n for nodes in OWNERS.values() for n in nodes]
    assert meta["demo"] is True and "us" in meta["countries"] and meta["dimensions"][0] == "demand"


def test_start_then_stream_to_the_first_pause(client):
    thread_id = start(client)
    assert client.get(f"/api/runs/{thread_id}").json()["live_from"] == 0

    events = sse(client.get(f"/api/runs/{thread_id}/events"))
    types = [e["type"] for e in events]
    assert types.count("caught_up") == 1 and types[-1] == "paused"
    # Token and Reasoning are queue-only, so none can come before the replay ends.
    assert not {"token", "reasoning"} & set(types[: types.index("caught_up")])
    assert events[-1]["pause"]["kind"] == "clarify"

    detail = wait_for(client, thread_id, "paused")
    assert detail["request_text"] == "Data Engineer" and detail["focus"] == ["skills"]
    assert detail["pause"]["kind"] == "clarify" and detail["run_log"][0]["node"] == "intake"
    assert [r["thread_id"] for r in client.get("/api/runs").json()] == [thread_id]
    # Nothing is live any more, so the stream closes without a retry.
    assert client.get(f"/api/runs/{thread_id}/events").status_code == 204


def test_unknown_run_is_a_404_in_the_one_body(client):
    for path in ("/api/runs/nope", "/api/runs/nope/events"):
        response = client.get(path)
        assert response.status_code == 404 and response.json()["code"] == "unknown_run"


def test_invalid_requests_are_reshaped(client):
    for body in ({"request_text": "  "}, {}):
        response = client.post("/api/runs", json=body)
        assert response.status_code == 422
        assert response.json()["code"] == "invalid_request"
        assert response.json()["errors"][0]["loc"][-1] == "request_text"


def test_guards_refuse_a_foreign_host_and_origin(client):
    assert client.get("/api/meta", headers={"Host": "evil.example"}).status_code == 400
    with_body = client.post("/api/runs", json={"request_text": "x"}, headers=FOREIGN)
    assert with_body.status_code == 403 and with_body.json()["code"] == "foreign_origin"
    assert client.post("/api/runs", headers=FOREIGN).status_code == 403
    assert client.get("/api/runs").json() == []  # neither created a Run
    assert client.post("/api/runs", json={"request_text": "x"}, headers={"Origin": "http://127.0.0.1"}).status_code == 201


def test_same_origin_passes_through_the_vite_dev_proxy(client):
    # changeOrigin: false leaves the browser's Host, so it still matches the Origin.
    proxied = {"Host": "localhost:5173", "Origin": "http://localhost:5173"}
    assert client.post("/api/runs", json={"request_text": "x"}, headers=proxied).status_code == 201


def test_posting_urls_are_http_only():
    assert web._http_url("https://example.com/a") == "https://example.com/a"
    assert web._http_url("javascript:alert(1)") is None


def test_the_app_is_served_with_a_real_404_for_api(client, tmp_path, monkeypatch):
    monkeypatch.setattr(web, "DIST", tmp_path / "missing")
    assert "npm --prefix web run build" in client.get("/runs/abc").text
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "index.html").write_text("<div id=root>", encoding="utf-8")
    monkeypatch.setattr(web, "DIST", tmp_path / "dist")
    assert client.get("/runs/abc").text == "<div id=root>"
    assert client.get("/api/nope").status_code == 404


def resume(client, thread_id, answer, status):
    response = client.post(f"/api/runs/{thread_id}/resume", json={"answer": answer})
    assert response.status_code == 200, response.text
    return wait_for(client, thread_id, status)


def to_plan_review(client, text="Data Engineer") -> str:
    thread_id = start(client, text)
    wait_for(client, thread_id, "paused")
    resume(client, thread_id, {"answers": ["Austin, Texas"]}, "paused")
    return thread_id


APPROVE = {"action": "approve", "plan": None, "feedback": None}


def test_every_pause_is_answered_to_done_and_the_brief_downloads(client):
    thread_id = to_plan_review(client)
    assert client.get(f"/api/runs/{thread_id}").json()["pause"]["kind"] == "plan_review"
    assert client.get(f"/api/runs/{thread_id}/brief.json").json()["code"] == "no_brief"

    assert resume(client, thread_id, APPROVE, "paused")["pause"]["kind"] == "low_data_review"
    done = resume(client, thread_id, {"action": "broaden", "guidance": "try remote"}, "done")
    assert done["brief"] and done["sample"]

    brief = client.get(f"/api/runs/{thread_id}/brief.json")
    assert brief.status_code == 200 and brief.json()["summary"] == done["brief"]["summary"]
    assert "attachment" in brief.headers["content-disposition"]
    assert client.get(f"/api/runs/{thread_id}/brief.md").text.startswith("# Market Brief")
    # Answered, so nothing is waiting any more.
    again = client.post(f"/api/runs/{thread_id}/resume", json={"answer": None})
    assert again.status_code == 409 and again.json()["code"] == "not_resumable"


def test_a_refused_answer_is_cleaned_and_leaves_the_run_paused(client):
    thread_id = to_plan_review(client)
    bad_plan = {"titles": ["x"], "country": "us", "location": "", "radius_km": 500, "max_days_old": 30,
                "target_postings": 20, "category": None}
    cases = [
        ({"action": "edit", "plan": bad_plan, "feedback": None}, ["plan", "radius_km"]),
        ({"action": "reject", "plan": None, "feedback": " "}, []),
        ({"action": "edit", "plan": None, "feedback": None}, []),
    ]
    for answer, loc in cases:
        response = client.post(f"/api/runs/{thread_id}/resume", json={"answer": answer})
        body = response.json()
        assert response.status_code == 422 and body["code"] == "invalid_answer"
        assert body["errors"][0]["loc"] == loc and not body["errors"][0]["msg"].startswith("Value error")
    missing = client.post(f"/api/runs/{thread_id}/resume", json={"answer": {"action": "approve"}}).json()
    assert {tuple(e["loc"]) for e in missing["errors"]} == {("plan",), ("feedback",)}
    assert client.get(f"/api/runs/{thread_id}").json()["record"]["status"] == "paused"
    # An edit with a valid plan carries on.
    good = {**bad_plan, "radius_km": 25, "titles": ["Platform Engineer"]}
    resume(client, thread_id, {"action": "edit", "plan": good, "feedback": None}, "paused")


def test_abort_ends_the_run_with_no_brief(client):
    thread_id = to_plan_review(client)
    detail = resume(client, thread_id, {"action": "abort", "plan": None, "feedback": None}, "aborted")
    assert detail["brief"] is None
    for kind in ("json", "md"):
        response = client.get(f"/api/runs/{thread_id}/brief.{kind}")
        assert response.status_code == 404 and response.json()["code"] == "no_brief"
    assert client.get("/api/runs/nope/brief.md").json()["code"] == "unknown_run"


def test_an_answer_for_a_run_that_is_not_waiting_is_refused(client):
    thread_id = to_plan_review(client, "Data Engineer, fail")
    resume(client, thread_id, APPROVE, "paused")
    resume(client, thread_id, {"action": "continue", "guidance": None}, "failed")
    refused = client.post(f"/api/runs/{thread_id}/resume", json={"answer": APPROVE})
    assert refused.status_code == 422 and "not waiting" in refused.json()["errors"][0]["msg"]
    resume(client, thread_id, None, "done")


def test_a_rejected_plan_comes_back_as_a_new_plan_review(client):
    thread_id = to_plan_review(client)
    detail = resume(client, thread_id, {"action": "reject", "plan": None, "feedback": "wider titles"}, "paused")
    assert detail["pause"]["kind"] == "plan_review" and len(detail["pause"]["payload"]["plan"]["titles"]) == 2


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [(RunLocked("abc"), 409, "run_locked"), (BalanceTooLow("low"), 402, "balance_too_low"), (httpx.ConnectError("down"), 502, "upstream")],
)
def test_resume_refusals_use_the_one_body(client, monkeypatch, error, status, code):
    async def refuse(*args, **kwargs):
        raise error

    monkeypatch.setattr(client.app.state.controller, "resume", refuse)
    response = client.post("/api/runs/abc/resume", json={"answer": None})
    assert response.status_code == status and response.json()["code"] == code
