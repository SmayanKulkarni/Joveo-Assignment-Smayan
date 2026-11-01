import type { RunState } from "./reducer"
import { stepLabel } from "./steps"
import { Turn } from "./Turn"
import type { Mode } from "./Turn"

export function Stream({ state, live }: { state: RunState; live: boolean }) {
  const { turns, texts, pause, ending } = state
  const last = turns.length - 1
  const modeOf = (i: number): Mode => {
    if (i < last || ending?.kind === "done") return "past"
    return live ? "live" : pause ? "waiting" : "open"
  }
  const items = turns.map((turn, i) => <Turn key={i} turn={turn} text={texts[i]} label={stepLabel(turn.step)} mode={modeOf(i)} />)
  const list = ending?.kind === "done" ? (
    // A finished Run reads as its Brief, with the route one click away.
    <details className="how">
      <summary>How this Run went</summary>
      <ol className="stream">{items}</ol>
    </details>
  ) : (
    <ol className="stream">{items}</ol>
  )
  return (
    // Announcing every token would be unusable, so the log is silent and a separate region speaks the milestones.
    <div role="log" aria-live="off">
      {list}
      {state.connection === "reconnecting" && <p className="pill reconnecting">Reconnecting…</p>}
    </div>
  )
}
