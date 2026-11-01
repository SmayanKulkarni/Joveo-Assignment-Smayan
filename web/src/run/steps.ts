import type { Graph } from "../api/types"

export type Step = {
  id: string
  label: string
  nodes: string[]
  sub: string // what an idle Step says it will do
  weight: number // its share of the progress bar; optional Steps never move it
  optional?: boolean
  wait?: string // what a waiting Step says
}

// Labels live here, while the topology comes from /meta. A node missing from this table fails a test.
export const STEPS: Step[] = [
  { id: "read", label: "Read your request", nodes: ["intake", "clarity_check"], sub: "Role, place, details", weight: 1 },
  { id: "ask", label: "Ask you", nodes: ["clarify"], sub: "Only if something is unclear", weight: 0, optional: true, wait: "Waiting for your answer" },
  { id: "plan", label: "Plan the search", nodes: ["plan"], sub: "Titles, area, dates", weight: 1 },
  { id: "approve", label: "Your approval", nodes: ["plan_review"], sub: "You review the plan", weight: 0.5, wait: "Waiting for you to approve" },
  { id: "search", label: "Search job boards", nodes: ["fetch_agent", "tools"], sub: "Adzuna, USAJOBS", weight: 3 },
  { id: "filter", label: "Filter postings", nodes: ["collect", "relevance"], sub: "Drop duplicates and misfits", weight: 1 },
  { id: "widen", label: "Widen the search", nodes: ["broaden"], sub: "Only if too few postings", weight: 0, optional: true },
  { id: "few", label: "Too few postings?", nodes: ["low_data_review"], sub: "You decide", weight: 0, optional: true, wait: "Waiting for you to decide" },
  { id: "postings", label: "Read postings", nodes: ["batch_extract"], sub: "Skills, seniority, pay", weight: 4 },
  { id: "normalise", label: "Tidy skill names", nodes: ["normalise_skills"], sub: "Merge spelling variants", weight: 1 },
  { id: "stats", label: "Compute the numbers", nodes: ["stats"], sub: "Medians, counts, shares", weight: 1 },
  { id: "write", label: "Write the brief", nodes: ["write_brief"], sub: "Summary and insights", weight: 2 },
  { id: "check", label: "Check every claim", nodes: ["critic"], sub: "Against the numbers", weight: 1 },
  { id: "finish", label: "Finish", nodes: ["render"], sub: "Brief ready", weight: 0.5 },
]

export const TOTAL_WEIGHT = STEPS.reduce((sum, step) => sum + step.weight, 0)

// The four bands, keyed by the owner /meta gives each node.
export const BANDS: Record<string, string> = { request_plan: "Understand", collection: "Collect", analysis: "Analyse", brief: "Brief" }

// The Steps grouped by the band their first node's owner puts them in, in order.
export function bandsOf(graph: Graph): { name: string; steps: Step[] }[] {
  const bands: { name: string; steps: Step[] }[] = []
  for (const step of STEPS) {
    const name = BANDS[graph.nodes.find((n) => n.id === step.nodes[0])?.owner ?? ""] ?? ""
    if (bands.at(-1)?.name === name) bands.at(-1)!.steps.push(step)
    else bands.push({ name, steps: [step] })
  }
  return bands
}

// Tool and source names the trace knows; anything else shows as it came.
const SOURCES: Record<string, string> = { search_adzuna: "Adzuna", adzuna: "Adzuna", search_usajobs: "USAJOBS", usajobs: "USAJOBS" }
export const sourceName = (name: string) => SOURCES[name] ?? name

const indexOfNode = new Map(STEPS.flatMap((step, i) => step.nodes.map((node) => [node, i] as const)))

export const stepOf = (node: string): Step | undefined => STEPS[indexOfNode.get(node) ?? -1]

export const stepIndex = (id: string) => STEPS.findIndex((s) => s.id === id)

export const stepLabel = (id: string) => STEPS.find((s) => s.id === id)?.label ?? id

// Nodes whose model output is a JSON draft: the stream shows this line instead of the fragments.
export const DRAFTING: Record<string, string> = {
  clarity_check: "Working out what's unclear…",
  plan: "Drafting the search plan…",
  broaden: "Working out how to widen the search…",
  write_brief: "Drafting the brief…",
  critic: "Checking claims against the numbers…",
}

// An edge to an earlier Step is a back-edge. Self-edges and the graph's START and END drop out.
export function backEdges(graph: Graph): string[] {
  const edges = graph.edges.flatMap(({ source, target }) => {
    const [from, to] = [indexOfNode.get(source), indexOfNode.get(target)]
    return from !== undefined && to !== undefined && to < from ? [`${STEPS[from].id}→${STEPS[to].id}`] : []
  })
  return [...new Set(edges)]
}
