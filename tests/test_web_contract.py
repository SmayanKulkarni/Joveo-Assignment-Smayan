import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from talent_scout.clients import web
from talent_scout.kernel.testing import make_settings
from talent_scout.runtime.graph import graph_topology
from test_web_api import APPROVE, sse, start, wait_for

TEST_DIR = Path(__file__).parents[1] / "web" / "src" / "test"
GRAPH = TEST_DIR / "meta-graph.json"
DEMO_RUN = TEST_DIR / "demo-run.json"


def test_the_graph_fixture_the_web_tests_use_matches_the_real_graph():
    # Vitest checks its Step labels against this file, so a new node must reach it.
    assert json.loads(GRAPH.read_text(encoding="utf-8")) == graph_topology()


def demo_run_feed(tmp_path) -> dict:
    settings = make_settings(demo=True, demo_delay=0, runs_db=tmp_path / "runs.sqlite", runs_dir=tmp_path / "runs")
    with TestClient(web.make_app(settings), base_url="http://127.0.0.1") as client:
        meta = client.get("/api/meta").json()
        thread_id = start(client)
        events = sse(client.get(f"/api/runs/{thread_id}/events"))
        for answer in ({"answers": ["Austin, Texas"]}, APPROVE, {"action": "broaden", "guidance": None}):
            wait_for(client, thread_id, "paused")
            client.post(f"/api/runs/{thread_id}/resume", json={"answer": answer})
            events += sse(client.get(f"/api/runs/{thread_id}/events"))
        wait_for(client, thread_id, "done")
    # Token, Reasoning and the caught_up marker depend on when the stream attached, so only buffered events are compared.
    events = [e for e in events if e["type"] not in ("token", "reasoning", "caught_up")]
    for event in events:
        if event["type"] == "done":
            event["paths"] = [Path(p).name for p in event["paths"]]  # the tmp directory differs per run
    return {"meta": {"graph": meta["graph"], "demo": meta["demo"]}, "events": events}


def test_the_demo_run_matches_the_feed_the_web_reducer_is_tested_with(tmp_path):
    feed = demo_run_feed(tmp_path)
    if os.environ.get("UPDATE_DEMO_RUN"):
        DEMO_RUN.write_text(json.dumps(feed, indent=1) + "\n", encoding="utf-8")
    assert json.loads(DEMO_RUN.read_text(encoding="utf-8")) == feed
