import json
from pathlib import Path

from talent_scout.runtime.graph import graph_topology

FIXTURE = Path(__file__).parents[1] / "web" / "src" / "test" / "meta-graph.json"


def test_the_graph_fixture_the_web_tests_use_matches_the_real_graph():
    # Vitest checks its Step labels against this file, so a new node must reach it.
    assert json.loads(FIXTURE.read_text(encoding="utf-8")) == graph_topology()
