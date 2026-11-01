import { useCallback, useEffect, useReducer, useRef, useState } from "react"
import { ApiError, cancelRun, getRun, resumeRun } from "../api/client"
import { isTerminal, openStream } from "../api/stream"
import type { RunDetail, RunRecord, RunStatus, WireEvent } from "../api/types"
import { refreshRuns } from "../sidebar/useRuns"
import { fromLog } from "./fromLog"
import { empty, reduce } from "./reducer"
import type { RunState } from "./reducer"

const RETRY_LOCKED_MS = 300
const SETTLE_TRIES = 5
const SETTLE_MS = 200
const FLUSH_TIMEOUT_MS = 250 // frames stop in a hidden tab
const ROW_LAG_MS = 300 // the sidebar row trails the event that ended the stream

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))
const notWaiting = (e: ApiError) => e.code === "invalid_answer" && e.errors.some((x) => x.msg.includes("not waiting"))
const keyOf = (record: RunRecord) => `${record.status}|${record.updated_at}`

// The row status a stream's last event leads to.
const ENDS_AS = (event: WireEvent): RunStatus | null =>
  event.type === "paused" ? "paused" : event.type === "stopped" ? "failed" : event.type === "done" ? event.status : null

// A Run being resumed holds its lock for a moment after its last step, so one retry usually clears run_locked.
async function postAnswer(id: string, answer: object | null) {
  try {
    return await resumeRun(id, answer)
  } catch (e) {
    if (!(e instanceof ApiError && e.code === "run_locked")) throw e
    await sleep(RETRY_LOCKED_MS)
    try {
      return await resumeRun(id, answer)
    } catch (again) {
      if (again instanceof ApiError && again.code === "run_locked") throw new ApiError(409, "run_locked", "This Run is open elsewhere")
      throw again
    }
  }
}

// `listed` is this Run's row in the sidebar, which is how a page with no stream hears of changes.
export function useRun(id: string, listed: RunRecord | undefined) {
  const [detail, setDetail] = useState<RunDetail | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [streaming, setStreaming] = useState(false)
  const [state, dispatch] = useReducer(reduce, empty)
  const latest = useRef(state)
  latest.current = state
  const closeStream = useRef(() => {})
  const mounted = useRef(true)
  const seen = useRef("") // the record the page last took in, as keyOf
  const endsAs = useRef<RunStatus | null>(null) // set once an event ended the stream, until the row catches up

  // Events are folded once per frame, so any token rate costs one render.
  const queue = useRef<WireEvent[]>([])
  const frame = useRef<{ raf: number; timer: number } | null>(null)
  const drop = useCallback(() => {
    if (frame.current) {
      cancelAnimationFrame(frame.current.raf)
      clearTimeout(frame.current.timer)
      frame.current = null
    }
    const events = queue.current
    queue.current = []
    return events
  }, [])
  const flush = useCallback(() => {
    const events = drop()
    if (events.length) dispatch({ type: "batch", events })
  }, [drop])
  const push = useCallback(
    (event: WireEvent) => {
      queue.current.push(event)
      frame.current ??= { raf: requestAnimationFrame(flush), timer: window.setTimeout(flush, FLUSH_TIMEOUT_MS) }
    },
    [flush],
  )

  const take = useCallback((run: RunDetail) => {
    seen.current = keyOf(run.record)
    setDetail(run)
  }, [])

  // The Run's end settles in the registry just after its event, so the detail is read again until it stops saying running.
  const settle = useCallback(async () => {
    for (let i = 0; i < SETTLE_TRIES; i++) {
      const run = await getRun(id)
      if (!mounted.current) return
      if (run.record.status !== "running" || i === SETTLE_TRIES - 1) return take(run)
      await sleep(SETTLE_MS)
    }
  }, [id, take])

  const load = useCallback(async () => {
    closeStream.current()
    drop()
    try {
      const run = await getRun(id)
      if (!mounted.current) return
      const base = fromLog(run)
      take(run)
      dispatch({ type: "reset", to: base })
      // Only a Run live in this server has a stream; any other shows what the detail holds.
      if (run.live_from !== null) connect(base)
      else setStreaming(false)
    } catch (e) {
      if (mounted.current) setError(e as Error)
    }
    // load and connect call each other; both only change with the id, and a page is keyed by it.
  }, [id, drop, take])

  const connect = useCallback(
    (base: RunState) => {
      closeStream.current()
      endsAs.current = null
      setStreaming(true)
      closeStream.current = openStream(id, {
        onEvent: (event) => {
          push(event)
          if (!isTerminal(event)) return
          flush()
          setStreaming(false)
          endsAs.current = ENDS_AS(event)
          setTimeout(refreshRuns, ROW_LAG_MS)
          if (event.type === "done") settle().catch((e) => mounted.current && setError(e))
        },
        // The replay starts over from this base. Live text stays, so a dropped connection keeps what is on screen.
        onOpen: () => {
          drop()
          dispatch({ type: "reset", to: base, keepTexts: true })
        },
        onReconnecting: () => dispatch({ type: "connection", to: "reconnecting" }),
        // Nothing is live (204, 404 or a server restart): the detail says what became of the Run.
        onClosed: () => void load(),
      })
    },
    [id, push, flush, drop, settle, load],
  )

  useEffect(() => {
    mounted.current = true
    load()
    return () => {
      mounted.current = false
      closeStream.current()
      drop()
    }
  }, [load, drop])

  // Another window moved the Run: with no stream of our own, take the new record and re-attach.
  useEffect(() => {
    if (!listed || streaming || !detail) return
    if (endsAs.current) {
      if (listed.status !== endsAs.current) return
      endsAs.current = null
      seen.current = keyOf(listed)
    } else if (keyOf(listed) !== seen.current) {
      seen.current = keyOf(listed)
      load()
    }
  }, [listed, streaming, detail, load])

  // Throws what the card or banner should show against itself. True once the Run has taken the answer, false if it had moved on already.
  async function post(payload: object | null) {
    setNotice(null)
    try {
      await postAnswer(id, payload)
      return true
    } catch (e) {
      if (!(e instanceof ApiError && (e.code === "not_resumable" || notWaiting(e)))) throw e
      setNotice("Answered elsewhere")
      await load()
      return false
    }
  }

  // The new stream starts from what is on screen, changed by the one thing the user just did.
  function carryOn(base: RunState) {
    refreshRuns()
    dispatch({ type: "reset", to: base, keepTexts: true })
    connect(base)
  }

  async function answer(payload: object, record: string) {
    if (await post(payload)) carryOn(reduce(latest.current, { type: "answered", record }))
  }

  // Resume retries the Step the Run stopped at, so it takes no answer.
  async function resume() {
    if (await post(null)) carryOn(reduce(latest.current, { type: "resumed" }))
  }

  // The Stopped event arrives on the stream, so there is nothing to do here but hear a refusal.
  async function stop() {
    try {
      await cancelRun(id)
    } catch (e) {
      // It ended in the moment before: the detail says how.
      if (e instanceof ApiError && e.code === "not_live") return load()
      setNotice((e as Error).message)
    }
  }

  return { detail, state, error, notice, streaming, answer, resume, stop }
}
