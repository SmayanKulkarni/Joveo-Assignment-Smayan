import type { Graph } from "../api/types"
import { bandsOf } from "../run/steps"
import type { Step } from "../run/steps"
import type { TraceState } from "../run/trace"

// Each mark differs in shape as well as colour.
const MARK = { idle: "○", active: "●", done: "✓", waiting: "⏸", failed: "✕" }

function bandStatus(trace: TraceState, steps: Step[]): keyof typeof MARK {
  const states = steps.map((s) => trace.steps[s.id].status)
  for (const status of ["failed", "waiting", "active"] as const) if (states.includes(status)) return status
  if (states.every((s) => s === "done" || s === "skipped")) return "done"
  return states.includes("done") ? "active" : "idle"
}

// The narrow screen's trace: four chips in place of the Steps.
export function StageStrip({ trace, graph }: { trace: TraceState; graph: Graph }) {
  return (
    <ol className="strip">
      {bandsOf(graph).map(({ name, steps }) => {
        const status = bandStatus(trace, steps)
        return (
          <li key={name} className={`chip-band ${status}`}>
            <span aria-hidden>{MARK[status]}</span> {name}
            <span className="sr-only"> ({status})</span>
          </li>
        )
      })}
    </ol>
  )
}
