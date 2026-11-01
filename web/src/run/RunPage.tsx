import { useEffect, useRef } from "react"
import { ApiError } from "../api/client"
import type { RunDetail, RunRecord } from "../api/types"
import { BriefView } from "../brief/BriefView"
import { PauseCard } from "../pause/PauseCard"
import { go } from "../router"
import { stepLabel, stepOf } from "./steps"
import { Stream } from "./Stream"
import type { RunState } from "./reducer"
import { useAutoScroll } from "./useAutoScroll"
import { useRun } from "./useRun"

const label = (node: string) => stepOf(node)?.label ?? node

// The last log line, else the registry's error: what `scout show` prints for an aborted Run.
const abortReason = (detail: RunDetail) => detail.run_log.at(-1)?.message ?? detail.record.error

// What the polite live region says: Step changes, Pauses and endings, never tokens.
function announcement({ turns, pause, ending }: RunState) {
  const step = turns.at(-1) && stepLabel(turns.at(-1)!.step)
  if (ending?.kind === "done") return "The Run is finished"
  if (ending?.kind === "aborted") return "The Run ended without a Brief"
  if (ending) return "The Run stopped"
  return pause ? `Waiting for you: ${step}` : (step ?? "")
}

export function RunPage({ id, listed }: { id: string; listed: RunRecord | undefined }) {
  const run = useRun(id, listed)
  const { detail, error } = run

  if (error instanceof ApiError && error.status === 404) {
    return (
      <p>
        Run not found. <a href="/" onClick={go}>Start a new Run</a>
      </p>
    )
  }
  if (error) return <p className="error">{error.message}</p>
  if (!detail) return null
  return <RunView {...run} id={id} detail={detail} />
}

type Loaded = Omit<ReturnType<typeof useRun>, "detail"> & { id: string; detail: RunDetail }

function RunView({ id, detail, state, notice, streaming, answer }: Loaded) {
  const { ending, pause } = state
  const live = streaming && !pause && !ending
  const { end, away, stuck, jump } = useAutoScroll(ending?.kind !== "done", state)
  const pauseBox = useRef<HTMLDivElement>(null)

  // A Pause that arrives while the reader is at the bottom takes focus, so a keyboard user lands on it.
  useEffect(() => {
    const heading = pauseBox.current?.querySelector<HTMLElement>("h2")
    if (pause && heading && stuck.current) {
      heading.tabIndex = -1
      heading.focus({ preventScroll: true })
    }
  }, [pause, stuck])

  const elsewhere = detail.record.status === "running" && detail.live_from === null && !streaming
  const reason = abortReason(detail)
  return (
    <>
      <div className="request">{detail.request_text ?? detail.record.summary}</div>
      <p className="sr-only" aria-live="polite">{announcement(state)}</p>
      <Stream state={state} live={live} />
      {elsewhere && <p className="notice">Running in another window</p>}
      {notice && <p className="notice">{notice}</p>}
      <div ref={pauseBox}>{pause && <PauseCard key={`${state.turns.length}-${pause.kind}`} pause={pause} send={answer} />}</div>
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
          Stopped{ending.node && ` at ${label(ending.node)}`}
          {ending.reason && `: ${ending.reason}`}
        </p>
      )}
      <div ref={end} />
      {away && (live || pause) && (
        <button className="jump" onClick={jump}>{pause ? "Waiting for you" : "Jump to latest"}</button>
      )}
    </>
  )
}
