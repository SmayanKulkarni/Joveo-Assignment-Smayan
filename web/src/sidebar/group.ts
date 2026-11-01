import type { RunRecord } from "../api/types"

export type RunGroup = { title: string; runs: RunRecord[] }

// Runs waiting on the user, so they are pinned and not repeated in the day groups.
export const needsYou = (run: RunRecord) => run.status === "paused" || run.status === "failed"

const DAY_MS = 864e5
const startOfDay = (date: Date) => new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime()

const titleFor = (daysAgo: number) =>
  daysAgo <= 0 ? "Today" : daysAgo === 1 ? "Yesterday" : daysAgo <= 7 ? "Previous 7 days" : "Earlier"

// Days are calendar days in the browser's timezone, not 24-hour spans. Rounding absorbs a day that is 23 or 25 hours long.
export function groupRuns(runs: RunRecord[], now = new Date()): { pinned: RunRecord[]; groups: RunGroup[] } {
  const newestFirst = [...runs].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
  const groups: RunGroup[] = []
  for (const run of newestFirst.filter((r) => !needsYou(r))) {
    const title = titleFor(Math.round((startOfDay(now) - startOfDay(new Date(run.updated_at))) / DAY_MS))
    const group = groups.find((g) => g.title === title)
    if (group) group.runs.push(run)
    else groups.push({ title, runs: [run] })
  }
  return { pinned: newestFirst.filter(needsYou), groups }
}
