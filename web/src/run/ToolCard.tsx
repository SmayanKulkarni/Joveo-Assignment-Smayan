import { useRef } from "react"
import { DUR, EASE, gsap, useAnimate, useMotion, usePrevious } from "../motion"
import type { Tool } from "./reducer"

const SOURCES: Record<string, string> = { adzuna: "Adzuna", usajobs: "USAJOBS" }
const sourceName = (name: string) => SOURCES[name.replace(/^search_/, "")] ?? name

export function ToolCard({ tool }: { tool: Tool }) {
  const state = tool.result !== null ? "done" : tool.interrupted ? "interrupted" : "running"
  const card = useRef<HTMLDivElement>(null)
  const animate = useAnimate()
  const before = usePrevious(state)

  useMotion(
    () => {
      if (!animate) return
      if (before === undefined) gsap.from(card.current, { y: 4, opacity: 0, duration: DUR.fast, ease: EASE.out })
      else if (state === "done") gsap.from(card.current!.querySelector("path"), { drawSVG: 0, duration: 0.35, ease: EASE.out })
    },
    [state],
    card,
  )
  return (
    <div ref={card} className={`tool ${state}`}>
      <span className="mark" aria-hidden>
        {state === "done" ? <svg viewBox="0 0 14 14"><path d="M3 7.5 L6 10.5 L11 4" /></svg> : state === "interrupted" ? "–" : ""}
      </span>
      <b>{sourceName(tool.name)}</b>
      <span>{tool.result ?? (state === "interrupted" ? "Interrupted" : tool.summary)}</span>
      {tool.pill && <span className="pill">{tool.pill}</span>}
    </div>
  )
}
