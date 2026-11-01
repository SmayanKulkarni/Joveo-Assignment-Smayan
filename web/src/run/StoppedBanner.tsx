import { Refusals } from "../pause/parts"
import { useSubmit } from "../pause/submit"
import { go } from "../router"
import type { Ending } from "./reducer"
import { stepOf } from "./steps"

export function StoppedBanner({ ending, resume }: { ending: Extract<Ending, { kind: "stopped" }>; resume: () => Promise<void> }) {
  // Resume takes no answer; the Pause forms' submit is only reused for its busy flag and refusals.
  const { busy, refusal, submit } = useSubmit(() => resume())
  const { node, reason } = ending
  const step = node && (stepOf(node)?.label ?? node)

  if (!step) {
    // Nothing was checkpointed, so there is nothing to pick up from.
    return (
      <div className="card">
        <h2>Stopped before anything was saved</h2>
        <a href="/" onClick={go}>Start a new Run</a>
      </div>
    )
  }
  return (
    <div className="card">
      <h2>{reason === "cancelled" ? `You stopped this Run at ${step}` : `Stopped at ${step}`}</h2>
      <p>Nothing is lost; Resume retries that step.</p>
      {reason && reason !== "cancelled" && (
        <details>
          <summary>What went wrong</summary>
          <p>{reason}</p>
        </details>
      )}
      <Refusals refusal={refusal} />
      <div className="actions">
        <button type="button" className="start" disabled={busy} onClick={() => submit({}, "")}>Resume</button>
      </div>
    </div>
  )
}
