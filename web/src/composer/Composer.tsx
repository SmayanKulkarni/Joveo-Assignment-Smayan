import { useState } from "react"
import type { KeyboardEvent } from "react"
import { startRun } from "../api/client"
import type { Dimension } from "../api/types"
import { DIMENSIONS } from "../dimensions"
import { navigate } from "../router"
import { refreshRuns } from "../sidebar/useRuns"

export function Composer() {
  const [text, setText] = useState("")
  const [focus, setFocus] = useState<Dimension[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const blank = !text.trim()

  async function submit() {
    if (blank || busy) return
    setBusy(true)
    setError(null)
    try {
      const { thread_id } = await startRun(text.trim(), focus)
      refreshRuns()
      navigate(`/runs/${thread_id}`)
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  function onKeyDown(event: KeyboardEvent) {
    // isComposing: Enter confirms an IME candidate, and must not send the request.
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  const toggle = (d: Dimension) => setFocus((f) => (f.includes(d) ? f.filter((x) => x !== d) : [...f, d]))

  return (
    <div className="composer-page">
      <h1>What market do you want to understand?</h1>
      <div className="composer">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="e.g. Senior data engineer in Austin, remote friendly, interested in pay"
          autoFocus
        />
        <div className="bottom">
          <div className="chips" role="group" aria-label="Focus">
            {DIMENSIONS.map(([d, name]) => (
              <button key={d} type="button" className="chip" aria-pressed={focus.includes(d)} onClick={() => toggle(d)}>
                {name}
              </button>
            ))}
          </div>
          <button type="button" className="start" disabled={blank || busy} onClick={submit}>
            Start
          </button>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  )
}
