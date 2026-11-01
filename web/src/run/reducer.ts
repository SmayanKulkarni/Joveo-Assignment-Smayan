import type { Pause, WireEvent } from "../api/types"
import { stepOf } from "./steps"

export type Turn = { step: string; notes: string[]; answer?: string }
export type Ending = { kind: "done" | "aborted" } | { kind: "stopped"; node: string | null; reason: string }
export type RunState = { turns: Turn[]; pause: Pause | null; ending: Ending | null }
// reset starts again from a base, and answered collapses the open Pause into a one-line record.
export type Action = WireEvent | { type: "reset"; to?: RunState } | { type: "answered"; record: string }

export const empty: RunState = { turns: [], pause: null, ending: null }

// A turn is one visit to one Step, so fetch_agent and tools share one.
function turnFor(turns: Turn[], node: string): Turn[] {
  const step = stepOf(node)?.id ?? node
  return turns.at(-1)?.step === step ? turns : [...turns, { step, notes: [] }]
}

export function reduce(state: RunState, action: Action): RunState {
  switch (action.type) {
    case "reset":
      return action.to ?? empty
    case "node_started":
      return { ...state, turns: turnFor(state.turns, action.node) }
    case "node_done": {
      const turns = turnFor(state.turns, action.node)
      const last = turns.at(-1)!
      return { ...state, turns: [...turns.slice(0, -1), { ...last, notes: [...last.notes, ...action.notes] }] }
    }
    case "paused":
      return { ...state, pause: action.pause }
    case "answered": {
      if (!state.pause) return state
      // A Pause kind is also its node's name. This clears the Pause locally, since the rerun node's NodeStarted wouldn't.
      const turns = turnFor(state.turns, state.pause.kind)
      const last = turns.at(-1)!
      return { ...state, pause: null, turns: [...turns.slice(0, -1), { ...last, answer: action.record }] }
    }
    case "done":
      return { ...state, ending: { kind: action.status } }
    case "stopped":
      return { ...state, ending: { kind: "stopped", node: action.node, reason: action.reason } }
    default:
      return state
  }
}
