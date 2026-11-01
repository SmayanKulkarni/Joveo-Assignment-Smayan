import { ApiError } from "../api/client"
import type { RunDetail } from "../api/types"
import { BriefView } from "../brief/BriefView"
import { PauseCard } from "../pause/PauseCard"
import { go } from "../router"
import { STEPS, stepOf } from "./steps"
import { useRun } from "./useRun"

const label = (node: string) => stepOf(node)?.label ?? node
// A turn holds a Step id, not a node name.
const stepLabel = (id: string) => STEPS.find((s) => s.id === id)?.label ?? id

// The last log line, else the registry's error: what `scout show` prints for an aborted Run.
const abortReason = (detail: RunDetail) => detail.run_log.at(-1)?.message ?? detail.record.error

export function RunPage({ id }: { id: string }) {
  const { detail, state, error, notice, streaming, answer } = useRun(id)

  if (error instanceof ApiError && error.status === 404) {
    return (
      <p>
        Run not found. <a href="/" onClick={go}>Start a new Run</a>
      </p>
    )
  }
  if (error) return <p className="error">{error.message}</p>
  if (!detail) return null

  const { ending, pause } = state
  const live = !pause && !ending && (streaming || detail.live_from !== null)
  const reason = abortReason(detail)
  return (
    <>
      <div className="request">{detail.request_text ?? detail.record.summary}</div>
      <ol className="stream">
        {state.turns.map((turn, i) => {
          const last = i === state.turns.length - 1
          return (
            <li key={i} className={live && last ? "turn active" : pause && last ? "turn waiting" : "turn"}>
              <b>{stepLabel(turn.step)}</b>
              {turn.notes.length > 0 && <span> · {turn.notes.join(" · ")}</span>}
              {turn.answer && <div className="answered">{turn.answer}</div>}
            </li>
          )
        })}
      </ol>
      {notice && <p className="notice">{notice}</p>}
      {pause && <PauseCard key={`${state.turns.length}-${pause.kind}`} pause={pause} send={answer} />}
      {ending?.kind === "done" &&
        (detail.brief ? <BriefView id={id} brief={detail.brief} sample={detail.sample} /> : <p>Finishing…</p>)}
      {ending?.kind === "aborted" && (
        <div className="card">
          <h2>This Run ended without a Brief</h2>
          {reason && <p>{reason}</p>}
          <a href="/" onClick={go}>Start a new Run</a>
        </div>
      )}
      {ending?.kind === "stopped" && (
        <p className="error">
          Stopped{ending.node && ` at ${label(ending.node)}`}: {ending.reason}
        </p>
      )}
    </>
  )
}
