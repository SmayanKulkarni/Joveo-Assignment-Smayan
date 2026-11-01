import { useEffect, useState } from "react"
import { Composer } from "./composer/Composer"
import { go, runIdOf, usePath } from "./router"
import { RunPage } from "./run/RunPage"
import { Sidebar } from "./sidebar/Sidebar"
import { needsYou } from "./sidebar/group"
import { useRuns } from "./sidebar/useRuns"

export function App() {
  const path = usePath()
  const id = runIdOf(path)
  const runs = useRuns()
  const [open, setOpen] = useState(false) // the slide-over, under about 900 px
  const waiting = runs.filter(needsYou).length

  // Opening a Run, or starting one, takes you out of the slide-over.
  useEffect(() => setOpen(false), [path])

  return (
    <div className="shell">
      <header className="topbar">
        <button onClick={() => setOpen(true)} aria-label={`Runs, ${waiting} need you`}>
          Runs{waiting > 0 && <span className="count">{waiting}</span>}
        </button>
        <a href="/" onClick={go}>Talent Scout</a>
      </header>
      <Sidebar runs={runs} activeId={id} open={open} />
      {open && <div className="scrim" onClick={() => setOpen(false)} />}
      <main>
        {id ? <RunPage id={id} key={id} listed={runs.find((run) => run.thread_id === id)} /> : <div className="column"><Composer /></div>}
      </main>
    </div>
  )
}
