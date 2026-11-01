import { useCallback, useEffect, useReducer, useRef, useState } from "react"
import { ApiError, getRun, resumeRun } from "../api/client"
import { openStream } from "../api/stream"
import type { RunDetail } from "../api/types"
import { empty, reduce } from "./reducer"
import type { RunState } from "./reducer"

const RETRY_LOCKED_MS = 300
const SETTLE_TRIES = 5
const SETTLE_MS = 200

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))
const notWaiting = (e: ApiError) => e.code === "invalid_answer" && e.errors.some((x) => x.msg.includes("not waiting"))

// A Run being resumed holds its lock for a moment after its last step, so one retry usually clears run_locked.
async function postAnswer(id: string, answer: object) {
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

// What a Run shows with no stream: a Pause still waiting, or an ending already reached.
function baseOf(run: RunDetail): RunState {
  if (run.pause) return reduce(empty, { type: "paused", pause: run.pause })
  const { status } = run.record
  return run.live_from === null && (status === "done" || status === "aborted") ? { ...empty, ending: { kind: status } } : empty
}

const endState = ({ pause, ending }: RunState) => ({ pause, ending })

export function useRun(id: string) {
  const [detail, setDetail] = useState<RunDetail | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [streaming, setStreaming] = useState(false)
  const [state, dispatch] = useReducer(reduce, empty)
  const latest = useRef(state)
  latest.current = state
  const closeStream = useRef(() => {})
  const mounted = useRef(true)

  // The Run's end settles in the registry just after its event, so the detail is read again until it stops saying running.
  const settle = useCallback(async () => {
    for (let i = 0; i < SETTLE_TRIES; i++) {
      const run = await getRun(id)
      if (!mounted.current) return
      if (run.record.status !== "running" || i === SETTLE_TRIES - 1) return setDetail(run)
      await sleep(SETTLE_MS)
    }
  }, [id])

  const connect = useCallback(
    (base: RunState) => {
      closeStream.current()
      setStreaming(true)
      closeStream.current = openStream(id, {
        onEvent: (event) => {
          dispatch(event)
          if (event.type === "done") settle().catch((e) => mounted.current && setError(e))
        },
        onOpen: () => dispatch({ type: "reset", to: base }), // the replay starts over from this base
        // 204: the Run ended before the stream opened. What happened is in the detail, so the screen keeps its turns and takes that.
        onClosed: () =>
          getRun(id)
            .then((run) => {
              if (!mounted.current) return
              setDetail(run)
              dispatch({ type: "reset", to: { ...latest.current, ...endState(baseOf(run)) } })
            })
            .catch((e) => mounted.current && setError(e)),
      })
    },
    [id, settle],
  )

  const load = useCallback(async () => {
    closeStream.current()
    try {
      const run = await getRun(id)
      if (!mounted.current) return
      const base = baseOf(run)
      setDetail(run)
      dispatch({ type: "reset", to: base })
      // Only a Run live in this server has a stream; any other shows what the detail holds.
      if (run.live_from !== null) connect(base)
    } catch (e) {
      if (mounted.current) setError(e as Error)
    }
  }, [id, connect])

  useEffect(() => {
    mounted.current = true
    load()
    return () => {
      mounted.current = false
      closeStream.current()
    }
  }, [load])

  // Throws what the card should show against itself; anything the Run has moved past is handled here.
  async function answer(payload: object, record: string) {
    setNotice(null)
    try {
      await postAnswer(id, payload)
    } catch (e) {
      if (e instanceof ApiError && (e.code === "not_resumable" || notWaiting(e))) {
        setNotice("Answered elsewhere")
        return load()
      }
      throw e
    }
    const base = reduce(latest.current, { type: "answered", record })
    dispatch({ type: "reset", to: base })
    connect(base)
  }

  return { detail, state, error, notice, streaming, answer }
}
