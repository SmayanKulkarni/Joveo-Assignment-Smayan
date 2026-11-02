import { useEffect, useState } from "react"
import type { KeyboardEvent } from "react"
import { getResume, startRun } from "../api/client"
import type { Dimension } from "../api/types"
import { DIMENSIONS } from "../dimensions"
import { navigate } from "../router"
import { refreshRuns } from "../sidebar/useRuns"

export function Composer({ customerId }: { customerId: string }) {
  const [text, setText] = useState("")
  const [focus, setFocus] = useState<Dimension[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [uploaded, setUploaded] = useState<string | null>(null)
  // With a Resume on file the Run can be drafted from it, so nothing has to be typed.
  const blank = !text.trim() && !uploaded

  // A Customer with no Resume answers 404, which just means there is no line to show.
  useEffect(() => {
    getResume(customerId).then((r) => setUploaded(r.uploaded_at), () => setUploaded(null))
  }, [customerId])

  async function submit() {
    if (blank || busy) return
    setBusy(true)
    setError(null)
    try {
      const { thread_id } = await startRun(customerId, text.trim(), focus)
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
      {uploaded && <p className="muted">Using the Resume uploaded on {new Date(uploaded).toLocaleDateString()}</p>}
      {error && <p className="error">{error}</p>}
    </div>
  )
}
