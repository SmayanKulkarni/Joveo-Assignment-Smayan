import type { Graph } from "../api/types"

// Labels live here, while the topology comes from /meta. A node missing from this table fails a test.
export const STEPS = [
  { id: "read", label: "Read your request", nodes: ["intake", "clarity_check"] },
  { id: "ask", label: "Ask you", nodes: ["clarify"] },
  { id: "plan", label: "Plan the search", nodes: ["plan"] },
  { id: "approve", label: "Your approval", nodes: ["plan_review"] },
  { id: "search", label: "Search job boards", nodes: ["fetch_agent", "tools"] },
  { id: "filter", label: "Filter postings", nodes: ["collect", "relevance"] },
  { id: "widen", label: "Widen the search", nodes: ["broaden"] },
  { id: "few", label: "Too few postings?", nodes: ["low_data_review"] },
  { id: "postings", label: "Read postings", nodes: ["batch_extract"] },
  { id: "normalise", label: "Tidy skill names", nodes: ["normalise_skills"] },
  { id: "stats", label: "Compute the numbers", nodes: ["stats"] },
  { id: "write", label: "Write the brief", nodes: ["write_brief"] },
  { id: "check", label: "Check every claim", nodes: ["critic"] },
  { id: "finish", label: "Finish", nodes: ["render"] },
]

const indexOfNode = new Map(STEPS.flatMap((step, i) => step.nodes.map((node) => [node, i] as const)))

export const stepOf = (node: string) => STEPS[indexOfNode.get(node) ?? -1]

// An edge to an earlier Step is a back-edge. Self-edges and the graph's START and END drop out.
export function backEdges(graph: Graph): string[] {
  const edges = graph.edges.flatMap(({ source, target }) => {
    const [from, to] = [indexOfNode.get(source), indexOfNode.get(target)]
    return from !== undefined && to !== undefined && to < from ? [`${STEPS[from].id}→${STEPS[to].id}`] : []
  })
  return [...new Set(edges)]
}
