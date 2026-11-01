import { DUR } from "../motion"
import { liveLine } from "../run/trace"
import type { TraceState } from "../run/trace"
import { Bar } from "./Bar"

export function ProgressBar({ trace }: { trace: TraceState }) {
  const percent = Math.round(trace.progress * 100)
  const waiting = trace.current !== null && trace.steps[trace.current].status === "waiting"
  const tone = trace.finished === "failed" ? "stopped" : waiting ? "waiting" : ""
  return (
    <div className="meter">
      <Bar value={percent} max={100} label="Run progress" className={tone} dur={DUR.slow} />
      <p className="muted">
        {liveLine(trace)} · {percent}%
      </p>
    </div>
  )
}
