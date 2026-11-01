import { memo, useState } from "react"
import type { Texts, Turn as TurnData } from "./reducer"
import { ToolCard } from "./ToolCard"

// live is the running turn, waiting holds a Pause, open is the last turn of an ended Run, and past is collapsed until clicked.
export type Mode = "live" | "waiting" | "open" | "past"

export const Turn = memo(function Turn({ turn, text, label, mode }: { turn: TurnData; text?: Texts; label: string; mode: Mode }) {
  const [expanded, setExpanded] = useState(false)
  const folded = mode === "past" && !expanded
  const title = (
    <>
      {mode === "past" && <span aria-hidden>✓ </span>}
      <b>{label}</b>
      {folded && turn.notes.length > 0 && <span> · {turn.notes.at(-1)}</span>}
    </>
  )
  if (folded) {
    return (
      <li className="turn past">
        <button className="fold" aria-expanded={false} onClick={() => setExpanded(true)}>{title}</button>
      </li>
    )
  }
  return (
    <li className={`turn ${mode}`}>
      {mode === "past" ? <button className="fold" aria-expanded onClick={() => setExpanded(false)}>{title}</button> : title}
      {mode === "waiting" && <span className="hint"> (waiting for you)</span>}
      {text?.thinking && (
        <details className="thinking">
          <summary>{mode === "live" && turn.node ? "Thinking…" : "Thought"}</summary>
          <p>{text.thinking}</p>
        </details>
      )}
      {turn.drafting && <p className="drafting">{turn.drafting}</p>}
      {text?.prose && <p className="prose">{text.prose}</p>}
      {turn.tools.map((tool, i) => <ToolCard key={i} tool={tool} />)}
      {turn.pills.length > 0 && <p>{turn.pills.map((pill) => <span key={pill} className="pill">{pill}</span>)}</p>}
      {turn.progress && (
        <p className="progress">
          <progress value={turn.progress.done} max={turn.progress.total} /> {turn.progress.done} of {turn.progress.total} batches
        </p>
      )}
      {turn.notes.length > 0 && <p className="notes">{turn.notes.join(" · ")}</p>}
      {turn.answer && <div className="answered">{turn.answer}</div>}
    </li>
  )
})
