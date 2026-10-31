from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore

from talent_scout.analysis.nodes import ROUTERS as ANALYSIS_ROUTERS
from talent_scout.analysis.nodes import fan_out
from talent_scout.analysis.nodes import make_nodes as analysis_nodes
from talent_scout.brief.nodes import ROUTERS as BRIEF_ROUTERS
from talent_scout.brief.nodes import make_nodes as brief_nodes
from talent_scout.collection.nodes import ROUTERS as COLLECTION_ROUTERS
from talent_scout.collection.nodes import make_nodes as collection_nodes
from talent_scout.kernel.state import State, owned
from talent_scout.request_plan.nodes import ROUTERS as REQUEST_PLAN_ROUTERS
from talent_scout.request_plan.nodes import make_nodes as request_plan_nodes
from talent_scout.runtime.deps import Deps, Node, Router
from talent_scout.runtime.testing import STUB_ROUTERS, stub_nodes

FAN_OUT_ROUTERS = ("relevance", "low_data_review")

EDGES = [
    (START, "intake"), ("intake", "clarity_check"), ("clarify", "intake"),
    ("plan", "plan_review"), ("tools", "fetch_agent"), ("collect", "relevance"),
    ("broaden", "fetch_agent"), ("batch_extract", "normalise_skills"), ("normalise_skills", "stats"),
    ("stats", "write_brief"),
    ("write_brief", "critic"), ("render", END),
]
# The targets are listed because a router returning Send can't be read for its destinations.
CONDITIONAL = {
    "clarity_check":   ["clarify", "plan", END],
    "plan_review":     ["fetch_agent", "plan", END],
    "fetch_agent":     ["tools", "collect"],
    "relevance":       ["batch_extract", "stats", "broaden", "low_data_review"],
    "low_data_review": ["broaden", "batch_extract", "stats", END],
    "critic":          ["write_brief", "render"],
}
OWNERS = {
    "request_plan": ["intake", "clarity_check", "clarify", "plan", "plan_review"],
    "collection":   ["fetch_agent", "tools", "collect", "relevance", "broaden", "low_data_review"],
    "analysis":     ["batch_extract", "normalise_skills", "stats"],
    "brief":        ["write_brief", "critic", "render"],
}
_OWNER_OF = {node: owner for owner, nodes in OWNERS.items() for node in nodes}


def _with_fan_out(router: Router) -> Router:
    # Collection returns "analyse" because Send payloads belong to Analysis, and a stage can't import another.
    def routed(state: State):
        out = router(state)
        return fan_out(state) if out == "analyse" else out

    return routed


def build_graph(deps: Deps, saver: BaseCheckpointSaver | None, store: BaseStore | None = None) -> CompiledStateGraph:
    # A landed stage's make_nodes(deps) and ROUTERS go here and override its stubs.
    real_nodes: dict[str, Node] = {}
    real_routers: dict[str, Router] = {}
    if not deps.stub_stages:
        real_nodes.update(request_plan_nodes(deps))
        real_routers.update(REQUEST_PLAN_ROUTERS)
        real_nodes.update(collection_nodes(deps))
        real_routers.update(COLLECTION_ROUTERS)
        real_nodes.update(analysis_nodes(deps))
        real_routers.update(ANALYSIS_ROUTERS)
        real_nodes.update(brief_nodes(deps))
        real_routers.update(BRIEF_ROUTERS)
    nodes = {**stub_nodes(), **real_nodes}
    routers = {**STUB_ROUTERS, **real_routers}
    for name in FAN_OUT_ROUTERS:
        routers[name] = _with_fan_out(routers[name])

    builder = StateGraph(State)
    for name, fn in nodes.items():
        builder.add_node(name, owned(name, _OWNER_OF[name])(fn))
    for source, target in EDGES:
        builder.add_edge(source, target)
    for source, targets in CONDITIONAL.items():
        builder.add_conditional_edges(source, owned(source, _OWNER_OF[source])(routers[source]), targets)
    return builder.compile(checkpointer=saver, store=store)
