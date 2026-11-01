import { liveLine } from "../run/trace"
import type { TraceState } from "../run/trace"

export function ProgressBar({ trace }: { trace: TraceState }) {
  const percent = Math.round(trace.progress * 100)
  const waiting = trace.current !== null && trace.steps[trace.current].status === "waiting"
  const tone = trace.finished === "failed" ? "stopped" : waiting ? "waiting" : ""
  return (
    <div className="meter">
      <div className={`bar ${tone}`} role="progressbar" aria-label="Run progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
        <i style={{ width: `${percent}%` }} />
      </div>
      <p className="muted">
        {liveLine(trace)} · {percent}%
      </p>
    </div>
  )
}
