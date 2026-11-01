import { useEffect, useRef } from "react"
import type { RunRecord, RunStatus } from "../api/types"
import { DUR, EASE, gsap, useMotion } from "../motion"
import { go } from "../router"
import { ago } from "../util"
import { groupRuns } from "./group"

// Every badge carries its word, so colour is never the only signal.
const BADGES: Record<RunStatus, { word: string; tone: string }> = {
  running: { word: "Running", tone: "blue" },
  paused: { word: "Needs you", tone: "amber" },
  failed: { word: "Stopped", tone: "red" },
  done: { word: "Done", tone: "green" },
  aborted: { word: "Aborted", tone: "grey" },
}

// was is the status in the previous list: a Row that moves between sections remounts, so it cannot remember it itself.
function Row({ run, active, bold, fresh, was }: { run: RunRecord; active: boolean; bold: boolean; fresh: boolean; was?: RunStatus }) {
  const badge = BADGES[run.status]
  const item = useRef<HTMLLIElement>(null)

  useMotion(
    () => {
      const find = gsap.utils.selector(item)
      if (run.status === "running") gsap.fromTo(find(".badge i"), { opacity: 1, scale: 1 }, { opacity: 0.25, scale: 0.7, duration: 0.6, ease: "sine.inOut", repeat: -1, yoyo: true })
      if (fresh) gsap.from(item.current, { opacity: 0, duration: DUR.base, ease: EASE.out })
      else if (was && was !== run.status) gsap.from(find(".badge"), { opacity: 0, duration: DUR.base, ease: EASE.out })
    },
    [run.status],
    item,
  )
  return (
    <li ref={item}>
      <a href={`/runs/${run.thread_id}`} onClick={go} aria-current={active ? "page" : undefined} className={bold ? "row bold" : "row"}>
        <span className="title">{run.summary}</span>
        <span className="meta">
          <span className={`badge ${badge.tone}`}>
            <i aria-hidden />
            {badge.word}
          </span>
          <time dateTime={run.updated_at}>{ago(run.updated_at)}</time>
        </span>
      </a>
    </li>
  )
}

export function Sidebar({ runs, activeId, open }: { runs: RunRecord[]; activeId: string | null; open: boolean }) {
  const { pinned, groups } = groupRuns(runs)
  // Only rows that appear after the first list count as new, so opening the app fades nothing.
  const known = useRef<Map<string, RunStatus> | null>(null)
  const seen = (run: RunRecord) => ({ fresh: known.current !== null && !known.current.has(run.thread_id), was: known.current?.get(run.thread_id) })
  useEffect(() => {
    if (runs.length > 0) known.current = new Map(runs.map((run) => [run.thread_id, run.status]))
  }, [runs])
  return (
    <nav className={open ? "sidebar open" : "sidebar"} aria-label="Runs">
      <a href="/" onClick={go} className="brand">Talent Scout</a>
      <a href="/" onClick={go} className="new-run">+ New Run</a>
      {pinned.length > 0 && (
        <section>
          <h2>Needs you</h2>
          <ul>{pinned.map((run) => <Row key={run.thread_id} run={run} active={run.thread_id === activeId} bold {...seen(run)} />)}</ul>
        </section>
      )}
      {groups.map((group) => (
        <section key={group.title}>
          <h2>{group.title}</h2>
          <ul>{group.runs.map((run) => <Row key={run.thread_id} run={run} active={run.thread_id === activeId} bold={false} {...seen(run)} />)}</ul>
        </section>
      ))}
    </nav>
  )
}
