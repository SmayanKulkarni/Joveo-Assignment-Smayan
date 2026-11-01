import type { Pause, WireEvent } from "../api/types"
import { DRAFTING, stepOf } from "./steps"
import { emptyTrace, traceReduce } from "./trace"
import type { TraceState } from "./trace"

export type Tool = { name: string; summary: string; result: string | null; pill?: string; interrupted?: boolean }
export type Turn = {
  step: string
  node: string | null // the node running now, so a gap in live text is only claimed where text could stream
  notes: string[]
  answer?: string
  tools: Tool[]
  pills: string[] // API calls that matched no card
  drafting: string | null
  progress?: { done: number; total: number }
}
// Live text sits apart from the turns, keyed by turn index, so a reset to a base can leave it alone.
export type Texts = { thinking: string; prose: string }
export type Ending = { kind: "done" | "aborted" } | { kind: "stopped"; node: string | null; reason: string }
export type RunState = {
  turns: Turn[]
  texts: Record<number, Texts>
  trace: TraceState
  pause: Pause | null
  ending: Ending | null
  connection: "live" | "reconnecting"
  animate: boolean // false until caught_up, and on any reopened Run
  gap: boolean
}
// reset starts again from a base, answered collapses the open Pause, resumed clears a Stopped ending, batch is one frame.
export type Action =
  | WireEvent
  | { type: "reset"; to?: RunState; keepTexts?: boolean }
  | { type: "answered"; record: string }
  | { type: "resumed" }
  | { type: "connection"; to: RunState["connection"] }
  | { type: "batch"; events: WireEvent[] }

export const empty: RunState = { turns: [], texts: {}, trace: emptyTrace, pause: null, ending: null, connection: "live", animate: false, gap: false }

export const newTurn = (step: string): Turn => ({ step, node: null, notes: [], tools: [], pills: [], drafting: null })

// A turn is one visit to one Step, so fetch_agent and tools share one.
export function turnFor(turns: Turn[], node: string): Turn[] {
  const step = stepOf(node)?.id ?? node
  return turns.at(-1)?.step === step ? turns : [...turns, newTurn(step)]
}

export const streams = (node: string | null) => node !== null && (node in DRAFTING || node === "fetch_agent")

// Changes the newest turn and leaves the rest as they are, so finished turns keep their identity for memo.
function patchLast(state: RunState, change: (turn: Turn) => Partial<Turn>): RunState {
  const i = state.turns.length - 1
  if (i < 0) return state
  return { ...state, turns: state.turns.map((turn, j) => (j === i ? { ...turn, ...change(turn) } : turn)) }
}

function addText(state: RunState, field: keyof Texts, text: string): RunState {
  const i = state.turns.length - 1
  if (i < 0) return state
  const current = state.texts[i] ?? { thinking: "", prose: "" }
  return { ...state, texts: { ...state.texts, [i]: { ...current, [field]: current[field] + text } } }
}

function apiPill(turn: Turn, source: string, text: string): Partial<Turn> {
  const at = turn.tools.findIndex((t) => t.name === `search_${source}` && !t.pill)
  if (at < 0) return { pills: [...turn.pills, `${source} · ${text}`] }
  return { tools: turn.tools.map((t, j) => (j === at ? { ...t, pill: text } : t)) }
}

export function reduce(state: RunState, action: Action): RunState {
  const next = fold(state, action)
  const trace = traceReduce(state.trace, action)
  return trace === state.trace ? next : { ...next, trace }
}

function fold(state: RunState, action: Action): RunState {
  switch (action.type) {
    case "reset":
      return { ...(action.to ?? empty), texts: action.keepTexts ? state.texts : {}, animate: false, connection: "live", gap: false }
    case "batch":
      return action.events.reduce(reduce, state)
    case "connection":
      return { ...state, connection: action.to }
    case "resumed":
      return { ...state, ending: null }
    case "node_started":
      return patchLast({ ...state, turns: turnFor(state.turns, action.node) }, () => ({
        node: action.node,
        drafting: DRAFTING[action.node] ?? null,
      }))
    case "node_done":
      return patchLast({ ...state, turns: turnFor(state.turns, action.node) }, (turn) => ({
        node: null,
        drafting: null,
        notes: [...turn.notes, ...action.notes],
      }))
    case "reasoning":
      return addText(state, "thinking", action.text)
    case "token": {
      const ended = patchLast(state, () => ({ drafting: null }))
      // A drafting node streams JSON, which is never shown; its first token only ends the drafting line.
      return action.node in DRAFTING ? ended : addText(ended, "prose", action.text)
    }
    case "tool_called":
      return patchLast(state, (turn) => ({ tools: [...turn.tools, { name: action.name, summary: action.summary, result: null }] }))
    case "tool_returned":
      // tools gathers its calls but returns them in call order, so the oldest open card of that name is the one.
      return patchLast(state, (turn) => {
        const at = turn.tools.findIndex((t) => t.name === action.name && t.result === null)
        return at < 0 ? {} : { tools: turn.tools.map((t, j) => (j === at ? { ...t, result: action.summary } : t)) }
      })
    case "api_called":
      return patchLast(state, (turn) => apiPill(turn, action.source, action.failed ? "failed" : action.cached ? "cached" : String(action.count)))
    case "extract_progress":
      return patchLast(state, () => ({ progress: { done: action.done, total: action.total } }))
    case "paused":
      return { ...state, pause: action.pause }
    case "answered": {
      if (!state.pause) return state
      // A Pause kind is also its node's name. This clears the Pause locally, since the rerun node's NodeStarted wouldn't.
      return patchLast({ ...state, pause: null, turns: turnFor(state.turns, state.pause.kind) }, () => ({ answer: action.record }))
    }
    case "done":
      return { ...state, ending: { kind: action.status } }
    case "stopped":
      return {
        ...state,
        ending: { kind: "stopped", node: action.node, reason: action.reason },
        turns: state.turns.map((turn) =>
          turn.tools.some((t) => t.result === null)
            ? { ...turn, tools: turn.tools.map((t) => (t.result === null ? { ...t, interrupted: true } : t)) }
            : turn,
        ),
      }
    case "caught_up": {
      // Live text sent before this point, or during an outage, is gone. Only say so where the active turn could have streamed.
      const i = state.turns.length - 1
      const lost = i >= 0 && streams(state.turns[i].node) && !state.pause && !state.ending && !state.texts[i]
      return { ...state, animate: true, gap: state.gap || lost }
    }
    default:
      return state
  }
}
