from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from talent_scout.kernel.state import State, owned
from talent_scout.request_plan.nodes import ROUTERS as REQUEST_PLAN_ROUTERS
from talent_scout.request_plan.nodes import make_nodes as request_plan_nodes
from talent_scout.runtime.deps import Deps, Node, Router
from talent_scout.runtime.testing import STUB_ROUTERS, stub_nodes

EDGES = [
    (START, "intake"), ("intake", "clarity_check"), ("clarify", "intake"),
    ("plan", "plan_review"), ("tools", "fetch_agent"), ("collect", "relevance"),
    ("broaden", "fetch_agent"), ("batch_extract", "stats"), ("stats", "write_brief"),
    ("write_brief", "critic"), ("render", END),
]
# The targets are listed because a router returning Send can't be read for its destinations.
CONDITIONAL = {
    "clarity_check":   ["clarify", "plan", END],
    "plan_review":     ["fetch_agent", "plan", END],
    "fetch_agent":     ["tools", "collect"],
    "relevance":       ["batch_extract", "broaden", "low_data_review"],
    "low_data_review": ["broaden", "batch_extract", "stats", END],
    "critic":          ["write_brief", "render"],
}
OWNERS = {
    "request_plan": ["intake", "clarity_check", "clarify", "plan", "plan_review"],
    "collection":   ["fetch_agent", "tools", "collect", "relevance", "broaden", "low_data_review"],
    "analysis":     ["batch_extract", "stats"],
    "brief":        ["write_brief", "critic", "render"],
}
_OWNER_OF = {node: owner for owner, nodes in OWNERS.items() for node in nodes}


def build_graph(deps: Deps, saver: BaseCheckpointSaver | None) -> CompiledStateGraph:
    # A landed stage's make_nodes(deps) and ROUTERS go here and override its stubs.
    real_nodes: dict[str, Node] = {}
    real_routers: dict[str, Router] = {}
    if not deps.stub_stages:
        real_nodes.update(request_plan_nodes(deps))
        real_routers.update(REQUEST_PLAN_ROUTERS)
    nodes = {**stub_nodes(), **real_nodes}
    routers = {**STUB_ROUTERS, **real_routers}

    builder = StateGraph(State)
    for name, fn in nodes.items():
        builder.add_node(name, owned(name, _OWNER_OF[name])(fn))
    for source, target in EDGES:
        builder.add_edge(source, target)
    for source, targets in CONDITIONAL.items():
        builder.add_conditional_edges(source, owned(source, _OWNER_OF[source])(routers[source]), targets)
    return builder.compile(checkpointer=saver)
