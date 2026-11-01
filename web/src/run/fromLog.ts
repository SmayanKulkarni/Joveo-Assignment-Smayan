import type { RunDetail } from "../api/types"
import { empty, newTurn, turnFor } from "./reducer"
import type { RunState, Turn } from "./reducer"
import { stepOf } from "./steps"

// These nodes write no log line in normal use, so the line that follows one implies it ran.
const IMPLIED: Record<string, string> = { collect: "search", normalise_skills: "postings" }

// The starting state for a Run with no stored events: its route and notes, but no tokens or tool cards.
export function fromLog({ record, pause, stopped_at, run_log, live_from }: RunDetail): RunState {
  const turns: Turn[] = []
  // A live handle replays everything from live_from, so only the lines before it are history.
  for (const line of run_log.slice(0, live_from ?? run_log.length)) {
    const step = stepOf(line.node)?.id ?? line.node
    const implied = IMPLIED[line.node]
    if (implied && turns.at(-1)?.step !== implied) turns.push(newTurn(implied))
    if (turns.at(-1)?.step !== step) turns.push(newTurn(step))
    turns.at(-1)!.notes.push(line.message)
  }
  const state: RunState = { ...empty, turns }
  if (pause) return { ...state, turns: turnFor(turns, pause.kind), pause }
  if (live_from !== null) return state
  const { status } = record
  if (status === "done" || status === "aborted") return { ...state, ending: { kind: status } }
  if (status === "failed") return { ...state, ending: { kind: "stopped", node: stopped_at, reason: record.error ?? "" } }
  return state
}
