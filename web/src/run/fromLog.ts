import type { RunDetail } from "../api/types"
import { empty, newTurn, turnFor } from "./reducer"
import type { Action, RunState, Turn } from "./reducer"
import { STEPS, stepOf } from "./steps"
import { traceReduce } from "./trace"

// These nodes write no log line in normal use, so the line that follows one implies it ran.
const IMPLIED: Record<string, string> = { collect: "search", normalise_skills: "postings" }

// The starting state for a Run with no stored events: its route and notes, but no tokens or tool cards.
export function fromLog({ record, pause, stopped_at, run_log, live_from }: RunDetail): RunState {
  const turns: Turn[] = []
  // A live handle replays everything from live_from, so only the lines before it are history.
  let previous = ""
  for (const line of run_log.slice(0, live_from ?? run_log.length)) {
    const step = stepOf(line.node)?.id ?? line.node
    const implied = IMPLIED[line.node]
    // A node that writes several lines implies its predecessor once, not once per line.
    if (implied && line.node !== previous && turns.at(-1)?.step !== implied) turns.push(newTurn(implied))
    if (turns.at(-1)?.step !== step) turns.push(newTurn(step))
    turns.at(-1)!.notes.push(line.message)
    previous = line.node
  }
  // Each turn replays as the events that would have made it, so a reload lands where the live trace would be.
  const events: Action[] = turns.flatMap(({ step, notes }) => {
    const node = STEPS.find((s) => s.id === step)?.nodes[0] ?? step
    return [{ type: "node_started", node }, { type: "node_done", node, notes }]
  })
  const state: RunState = { ...empty, turns }
  const withTrace = (...more: Action[]) => ({ ...state, trace: [...events, ...more].reduce(traceReduce, empty.trace) })
  if (pause) return { ...withTrace({ type: "paused", pause }), turns: turnFor(turns, pause.kind), pause }
  if (live_from !== null) return withTrace()
  const { status } = record
  if (status === "done" || status === "aborted") return { ...withTrace({ type: "done", status, paths: [] }), ending: { kind: status } }
  if (status === "failed") {
    const reason = record.error ?? ""
    return { ...withTrace({ type: "stopped", node: stopped_at, reason }), ending: { kind: "stopped", node: stopped_at, reason } }
  }
  return withTrace()
}
