import { useEffect, useRef, useState } from "react"
import { ApiError, deleteRun } from "../api/client"
import { useMeta } from "../api/useMeta"
import type { Customer, RunDetail, RunRecord } from "../api/types"
import { CustomerHeader } from "../customers/CustomerHeader"
import { Deliverables } from "../brief/Deliverables"
import { PauseCard } from "../pause/PauseCard"
import { AnimateContext } from "../motion"
import { go, navigate } from "../router"
import { refreshRuns } from "../sidebar/useRuns"
import { ProgressBar } from "../trace/ProgressBar"
import { StageStrip } from "../trace/StageStrip"
import { TracePanel } from "../trace/TracePanel"
import { stepLabel } from "./steps"
import { StoppedBanner } from "./StoppedBanner"
import { Stream } from "./Stream"
import type { RunState } from "./reducer"
import { useAutoScroll } from "./useAutoScroll"
import { useNarrow } from "./useNarrow"
import { useRun } from "./useRun"
import { ask } from "../confirm"

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

export function RunPage({ id, listed, customer }: { id: string; listed: RunRecord | undefined; customer: Customer | undefined }) {
  const run = useRun(id, listed)
  const { detail, error } = run

  if (error instanceof ApiError && error.status === 404) {
    return (
      <p>
        Run not found. <a href="/" onClick={go}>Back to Customers</a>
      </p>
    )
  }
  if (error) return <p className="error">{error.message}</p>
  if (!detail) return null
  return <RunView {...run} id={id} detail={detail} customer={customer} />
}

type Loaded = Omit<ReturnType<typeof useRun>, "detail"> & { id: string; detail: RunDetail; customer: Customer | undefined }

function RunView({ id, detail, customer, state, notice, streaming, answer, resume, stop }: Loaded) {
  const { ending, pause } = state
  const live = streaming && !pause && !ending
  const { end, away, stuck, jump } = useAutoScroll(ending?.kind !== "done", state)
  const pauseBox = useRef<HTMLDivElement>(null)
  const meta = useMeta()
  const narrow = useNarrow()
  const [stopping, setStopping] = useState(false)

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
  const toPause = () => pauseBox.current?.scrollIntoView({ block: "nearest", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" })
  return (
    <AnimateContext.Provider value={state.animate}>
    <div className="run">
      <div className={`column${ending?.kind === "done" ? " wide" : ""}`}>
        {meta && narrow && (
          <div className="trace-strip">
            <StageStrip trace={state.trace} graph={meta.graph} />
            <ProgressBar trace={state.trace} />
          </div>
        )}
        {customer && <CustomerHeader customer={customer} />}
        <div className="run-head">
          <div className="request">{detail.request_text ?? detail.record.summary}</div>
          {live && (
            <button
              type="button"
              className="danger"
              disabled={stopping}
              onClick={() => {
                setStopping(true)
                stop().finally(() => setStopping(false))
              }}
            >
              Stop
            </button>
          )}
        </div>
        {!live && detail.record.status !== "running" && (
          <button
            type="button"
            className="danger no-print"
            onClick={async () => {
              if (!(await ask("Delete this Run? This can't be undone.", "Delete Run"))) return
              await deleteRun(id)
              refreshRuns()
              navigate(customer ? `/customers/${customer.id}` : "/")
            }}
          >
            Delete Run
          </button>
        )}
        <p className="sr-only" aria-live="polite">{announcement(state)}</p>
        <Stream state={state} live={live} />
        {elsewhere && <p className="notice">Running in another window</p>}
        {notice && <p className="notice">{notice}</p>}
        <div ref={pauseBox}>{pause && <PauseCard key={`${state.turns.length}-${pause.kind}`} pause={pause} send={answer} />}</div>
        {ending?.kind === "done" &&
          (detail.brief ? <Deliverables id={id} detail={{ ...detail, brief: detail.brief }} /> : <p>Finishing…</p>)}
        {ending?.kind === "aborted" && (
          <div className="card">
            <h2>This Run ended without a Brief</h2>
            {reason && <p>{reason}</p>}
            <a href="/" onClick={go}>Back to Customers</a>
          </div>
        )}
        {ending?.kind === "stopped" && <StoppedBanner ending={ending} resume={resume} />}
        <div ref={end} />
        {away && (live || pause) && (
          <button className="jump" onClick={jump}>{pause ? "Waiting for you" : "Jump to latest"}</button>
        )}
      </div>
      {meta && !narrow && <TracePanel trace={state.trace} graph={meta.graph} onJump={toPause} />}
    </div>
    </AnimateContext.Provider>
  )
}
