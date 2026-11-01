import type { RunRecord, RunStatus } from "../api/types"
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

function Row({ run, active, bold }: { run: RunRecord; active: boolean; bold: boolean }) {
  const badge = BADGES[run.status]
  return (
    <li>
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
  return (
    <nav className={open ? "sidebar open" : "sidebar"} aria-label="Runs">
      <a href="/" onClick={go} className="brand">Talent Scout</a>
      <a href="/" onClick={go} className="new-run">+ New Run</a>
      {pinned.length > 0 && (
        <section>
          <h2>Needs you</h2>
          <ul>{pinned.map((run) => <Row key={run.thread_id} run={run} active={run.thread_id === activeId} bold />)}</ul>
        </section>
      )}
      {groups.map((group) => (
        <section key={group.title}>
          <h2>{group.title}</h2>
          <ul>{group.runs.map((run) => <Row key={run.thread_id} run={run} active={run.thread_id === activeId} bold={false} />)}</ul>
        </section>
      ))}
    </nav>
  )
}
