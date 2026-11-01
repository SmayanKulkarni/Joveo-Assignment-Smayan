import { expect, test } from "vitest"
import type { Pause, RunDetail, RunStatus } from "../api/types"
import { fromLog } from "../run/fromLog"

const line = (node: string, message = node) => ({ node, kind: "note", message })

function detail(status: RunStatus, over: Partial<RunDetail> = {}): RunDetail {
  return {
    record: { thread_id: "t", summary: "s", status, error: null, created_at: "", updated_at: "" },
    request_text: "r", focus: [], pause: null, stopped_at: null, run_log: [], live_from: null, brief: null, sample: [], ...over,
  }
}

const steps = (d: RunDetail) => fromLog(d).turns.map((t) => t.step)

test("log lines group into turns by consecutive Step", () => {
  const run_log = [line("intake"), line("clarity_check"), line("plan"), line("relevance"), line("broaden")]
  expect(steps(detail("running", { run_log }))).toEqual(["read", "plan", "filter", "widen"])
})

test("collect implies search and normalise_skills implies postings", () => {
  const run_log = [line("plan"), line("collect"), line("relevance"), line("normalise_skills")]
  expect(steps(detail("running", { run_log }))).toEqual(["plan", "search", "filter", "postings", "normalise"])
})

test("only the lines before live_from are history", () => {
  const run_log = [line("intake"), line("plan"), line("collect")]
  expect(steps(detail("running", { run_log, live_from: 2 }))).toEqual(["read", "plan"])
  expect(steps(detail("running", { run_log, live_from: 0 }))).toEqual([])
})

test("each status places the cursor", () => {
  const pause: Pause = { kind: "plan_review", payload: { plan: {} as never, assumptions: [] } }
  const paused = fromLog(detail("paused", { pause, run_log: [line("plan")] }))
  expect(paused.pause).toBe(pause)
  expect(paused.turns.map((t) => t.step)).toEqual(["plan", "approve"])

  expect(fromLog(detail("done")).ending).toEqual({ kind: "done" })
  expect(fromLog(detail("aborted")).ending).toEqual({ kind: "aborted" })
  expect(fromLog(detail("failed", { stopped_at: "stats" })).ending).toMatchObject({ kind: "stopped", node: "stats" })
  // Live here: the stream decides, so there is no ending yet.
  expect(fromLog(detail("running", { live_from: 0 })).ending).toBeNull()
  expect(fromLog(detail("done", { live_from: 3 })).ending).toBeNull()
})
