import { useCallback, useEffect, useState } from "react"
import { listRuns } from "../api/client"
import type { RunRecord } from "../api/types"

const REFRESH = "runs:refresh"
const FAST_MS = 3000
const SLOW_MS = 15000

// Anything that changes a Run (start, resume, cancel, a stream's end) calls this instead of waiting for the poll.
export const refreshRuns = () => dispatchEvent(new Event(REFRESH))

// The sidebar polls and never opens a stream: browsers allow only about six connections per origin.
export function useRuns(): RunRecord[] {
  const [runs, setRuns] = useState<RunRecord[]>([])
  const load = useCallback(() => {
    // A failed poll leaves the list as it was, and the next one tries again.
    listRuns().then(setRuns, () => {})
  }, [])
  const anyRunning = runs.some((run) => run.status === "running")

  useEffect(() => {
    load()
    const timer = setInterval(load, anyRunning ? FAST_MS : SLOW_MS)
    addEventListener("focus", load)
    addEventListener(REFRESH, load)
    return () => {
      clearInterval(timer)
      removeEventListener("focus", load)
      removeEventListener(REFRESH, load)
    }
  }, [anyRunning, load])

  return runs
}
