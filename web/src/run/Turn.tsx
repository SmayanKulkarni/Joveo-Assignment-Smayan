import { memo, useRef, useState } from "react"
import { DUR, EASE, gsap, useAnimate, useMotion } from "../motion"
import { streams } from "./reducer"
import type { Texts, Turn as TurnData } from "./reducer"
import { Bar } from "../trace/Bar"
import { ToolCard } from "./ToolCard"

// The only motion on prose: a stepped blink, gone as soon as the turn stops being live.
function Caret() {
  const ref = useRef<HTMLSpanElement>(null)
  useMotion(() => void gsap.to(ref.current, { opacity: 0, duration: DUR.slow, ease: "steps(1)", repeat: -1, yoyo: true }), [], ref)
  return <span ref={ref} className="caret" aria-hidden />
}

// live is the running turn, waiting holds a Pause, open is the last turn of an ended Run, and past is collapsed until clicked.
export type Mode = "live" | "waiting" | "open" | "past"

export const Turn = memo(function Turn({ turn, text, label, mode }: { turn: TurnData; text?: Texts; label: string; mode: Mode }) {
  const [expanded, setExpanded] = useState(false)
  const item = useRef<HTMLLIElement>(null)
  const animate = useAnimate()
  // A turn is a one-shot on arrival only; folding and unfolding keep the same element.
  useMotion(() => void (animate && gsap.from(item.current, { y: 6, opacity: 0, duration: DUR.base, ease: EASE.out })), [], item)
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
      <li ref={item} className="turn past">
        <button className="fold" aria-expanded={false} onClick={() => setExpanded(true)}>{title}</button>
      </li>
    )
  }
  return (
    <li ref={item} className={`turn ${mode}`}>
      {mode === "past" ? <button className="fold" aria-expanded onClick={() => setExpanded(false)}>{title}</button> : title}
      {mode === "waiting" && <span className="hint"> (waiting for you)</span>}
      {text?.thinking && (
        <details className="thinking">
          <summary>{mode === "live" && turn.node ? "Thinking…" : "Thought"}</summary>
          <p>{text.thinking}</p>
        </details>
      )}
      {turn.drafting && <p className="drafting">{turn.drafting}</p>}
      {text?.prose && (
        <p className="prose">
          {text.prose}
          {mode === "live" && streams(turn.node) && <Caret />}
        </p>
      )}
      {turn.tools.map((tool, i) => <ToolCard key={i} tool={tool} />)}
      {turn.pills.length > 0 && <p>{turn.pills.map((pill) => <span key={pill} className="pill">{pill}</span>)}</p>}
      {turn.progress && (
        <p className="progress">
          <Bar value={turn.progress.done} max={turn.progress.total} label="Batches read" className="mini" /> {turn.progress.done} of {turn.progress.total} batches
        </p>
      )}
      {turn.notes.length > 0 && <p className="notes">{turn.notes.join(" · ")}</p>}
      {turn.answer && <div className="answered">{turn.answer}</div>}
    </li>
  )
})
