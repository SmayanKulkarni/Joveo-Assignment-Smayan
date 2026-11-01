import { expect, test } from "vitest"
import type { RunRecord, RunStatus } from "../api/types"
import { groupRuns } from "../sidebar/group"

// Built from local-time parts, so the test means the same in any timezone.
const NOW = new Date(2026, 10, 15, 0, 30)
const at = (daysAgo: number, hour: number, minute = 0) => new Date(2026, 10, 15 - daysAgo, hour, minute).toISOString()
const run = (id: string, status: RunStatus, updated_at: string): RunRecord => ({
  thread_id: id, summary: id, status, error: null, created_at: updated_at, updated_at,
})

test("days are calendar days in local time, so 23:59 yesterday is not Today", () => {
  const { groups } = groupRuns(
    [run("a", "done", at(0, 0, 5)), run("b", "done", at(1, 23, 59)), run("c", "done", at(7, 12)), run("d", "done", at(8, 12))],
    NOW,
  )
  expect(groups.map((g) => [g.title, g.runs.map((r) => r.thread_id)])).toEqual([
    ["Today", ["a"]], ["Yesterday", ["b"]], ["Previous 7 days", ["c"]], ["Earlier", ["d"]],
  ])
})

test("paused and failed Runs are pinned newest first and not repeated below", () => {
  const { pinned, groups } = groupRuns(
    [run("old", "paused", at(3, 9)), run("fresh", "failed", at(0, 0, 10)), run("ok", "done", at(0, 0, 20)), run("go", "running", at(0, 0, 25))],
    NOW,
  )
  expect(pinned.map((r) => r.thread_id)).toEqual(["fresh", "old"])
  expect(groups).toHaveLength(1)
  expect(groups[0].runs.map((r) => r.thread_id)).toEqual(["go", "ok"])
})
