import type { Action } from "./reducer"
import { STEPS, TOTAL_WEIGHT, stepIndex, stepLabel, stepOf } from "./steps"

export type StepStatus = "idle" | "active" | "done" | "waiting" | "failed" | "skipped"
export type StepTrace = { status: StepStatus; visits: number; note: string }
export type Source = { cached: boolean; count: number; failed: boolean }
export type TraceState = {
  steps: Record<string, StepTrace>
  current: string | null
  looped: string[] // back-edges the Run has taken, as "from→to"
  loops: number // every traversal, so a repeated edge can still be told apart
  lastLoop: string | null
  tool: { name: string; summary: string } | null // the call in flight
  sources: Record<string, Source>
  extract: { done: number; total: number }
  progress: number
  finished: "done" | "aborted" | "failed" | null
}

const ACTIVE_SHARE = 0.35 // how much of its weight a running Step has earned

const idle = (visits = 0): StepTrace => ({ status: "idle", visits, note: "" })

export const emptyTrace: TraceState = {
  steps: Object.fromEntries(STEPS.map((s) => [s.id, idle()])),
  current: null,
  looped: [],
  loops: 0,
  lastLoop: null,
  tool: null,
  sources: {},
  extract: { done: 0, total: 0 },
  progress: 0,
  finished: null,
}

function patch(trace: TraceState, id: string, change: Partial<StepTrace>): TraceState {
  return { ...trace, steps: { ...trace.steps, [id]: { ...trace.steps[id], ...change } } }
}

function enter(trace: TraceState, id: string): TraceState {
  // The same Step again is a retry or a rerun after an answer, not a new visit.
  if (trace.current === id) return trace.steps[id].status === "active" ? trace : patch(trace, id, { status: "active" })

  const steps = { ...trace.steps }
  const to = stepIndex(id)
  let { looped, loops, lastLoop } = trace
  if (trace.current) {
    const from = stepIndex(trace.current)
    if (steps[trace.current].status === "active" || steps[trace.current].status === "waiting") steps[trace.current] = { ...steps[trace.current], status: "done" }
    if (to < from) {
      // A loop: everything from the target to where the Run was runs again, except optional Steps that already ran.
      lastLoop = `${trace.current}→${id}`
      looped = [...new Set([...looped, lastLoop])]
      loops += 1
      for (const step of STEPS.slice(to + 1, from + 1)) {
        if (steps[step.id].status === "done" && !step.optional) steps[step.id] = idle(steps[step.id].visits)
      }
    }
  }
  // Behind the Run, a Step that never started either wasn't needed (optional), or ran without an event to show it (a reload).
  for (const step of STEPS.slice(0, to)) {
    const t = steps[step.id]
    if (t.status === "idle") steps[step.id] = step.optional ? { ...t, status: "skipped" } : { ...t, status: "done", visits: Math.max(1, t.visits) }
  }
  steps[id] = { status: "active", visits: steps[id].visits + 1, note: "" }

  return {
    ...trace,
    steps,
    looped,
    loops,
    lastLoop,
    current: id,
    tool: null,
    sources: id === "search" ? {} : trace.sources,
    extract: id === "postings" ? { done: 0, total: 0 } : trace.extract,
  }
}

function apply(trace: TraceState, action: Action): TraceState {
  switch (action.type) {
    case "node_started": {
      const step = stepOf(action.node)
      return step ? enter(trace, step.id) : trace
    }
    case "node_done": {
      const step = stepOf(action.node)
      const note = action.notes.at(-1)
      return step && note ? patch(trace, step.id, { note }) : trace
    }
    case "tool_called":
      return { ...trace, tool: { name: action.name, summary: action.summary } }
    case "tool_returned":
      return { ...trace, tool: null }
    case "api_called":
      return { ...trace, sources: { ...trace.sources, [action.source]: { cached: action.cached, count: action.count, failed: action.failed } } }
    case "extract_progress":
      return { ...trace, extract: { done: action.done, total: action.total } }
    case "paused": {
      // A Pause kind is also its node's name, and the Pause marks only its own Step.
      const id = stepOf(action.pause.kind)!.id
      return patch(enter(trace, id), id, { status: "waiting" })
    }
    case "answered": {
      const waiting = STEPS.find((s) => trace.steps[s.id].status === "waiting")
      return waiting ? patch(trace, waiting.id, { status: "active" }) : trace
    }
    case "resumed": {
      const failed = STEPS.find((s) => trace.steps[s.id].status === "failed")
      return { ...(failed ? patch(trace, failed.id, { status: "active" }) : trace), finished: null }
    }
    case "done": {
      const steps = { ...trace.steps }
      for (const step of STEPS) {
        const { status } = steps[step.id]
        if (step.id === trace.current && (status === "active" || status === "waiting")) steps[step.id] = { ...steps[step.id], status: "done" }
        // An abort leaves the rest untouched: those Steps never had a chance to run.
        else if (status === "idle" && (step.optional || action.status === "done")) steps[step.id] = { ...steps[step.id], status: step.optional ? "skipped" : "done" }
      }
      return { ...trace, steps, tool: null, finished: action.status }
    }
    case "stopped": {
      const id = (action.node && stepOf(action.node)?.id) || trace.current
      return { ...(id ? patch(id === trace.current ? trace : enter(trace, id), id, { status: "failed" }) : trace), tool: null, finished: "failed" }
    }
    default:
      return trace
  }
}

function earned(trace: TraceState): number {
  const sum = STEPS.reduce((total, step) => {
    const { status } = trace.steps[step.id]
    if (status === "done") return total + step.weight
    if (status !== "active") return total
    const { done, total: batches } = trace.extract
    return total + step.weight * (step.id === "postings" && batches ? done / batches : ACTIVE_SHARE)
  }, 0)
  return sum / TOTAL_WEIGHT
}

// The bar only moves forward, even when a loop sends Steps back to idle.
export function traceReduce(trace: TraceState, action: Action): TraceState {
  const next = apply(trace, action)
  if (next === trace) return trace
  return { ...next, progress: Math.max(trace.progress, next.finished === "done" ? 1 : earned(next)) }
}

// The line under the bar, naming the live Step.
export function liveLine({ current, steps, finished }: TraceState): string {
  const label = current && stepLabel(current)
  if (finished === "done") return "Done"
  if (finished === "aborted") return "Ended without a Brief"
  if (finished === "failed") return label ? `Stopped at ${label}` : "Stopped"
  if (!current) return "Starting…"
  return steps[current].status === "waiting" ? `Waiting for you: ${label}` : `${label}…`
}
