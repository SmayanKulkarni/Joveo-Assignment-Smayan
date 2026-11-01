import { useRef } from "react"
import { DUR, EASE, gsap, useAnimate, useMotion, usePrevious } from "../motion"
import type { Step } from "../run/steps"
import { sourceName } from "../run/steps"
import type { StepStatus, StepTrace, TraceState } from "../run/trace"
import { Bar } from "./Bar"

export const GEOMETRY = { railX: 22, nodeX: 44, nodeW: 214, iconY: 24, iconR: 9 }
const { railX, nodeX, nodeW, iconY, iconR } = GEOMETRY

function Icon({ status, y }: { status: StepStatus; y: number }) {
  return (
    <g className="icon" transform={`translate(${railX} ${y + iconY})`} aria-hidden>
      <circle r={iconR} />
      {(status === "active" || status === "waiting") && <circle r={iconR} className="ring" />}
      {status === "active" && <circle r={iconR} className="arc" strokeDasharray="30 27" />}
      {status === "done" && <path className="check" d="M-4 0.5 L-1 3.5 L4.5 -3" />}
      {status === "waiting" && <path d="M-3 -4 V4 M3 -4 V4" />}
      {status === "failed" && <path d="M-3.5 -3.5 L3.5 3.5 M3.5 -3.5 L-3.5 3.5" />}
      {status === "skipped" && <path d="M-4 0 H4" />}
    </g>
  )
}

function statusLine(step: Step, { status, note }: StepTrace) {
  switch (status) {
    case "idle": return step.sub
    case "active": return note || "Working…"
    case "done": return note || "Done"
    case "waiting": return step.wait ?? "Waiting for you"
    case "failed": return "Stopped. Resume retries it"
    case "skipped": return "Not needed"
  }
}

function Sources({ trace: { tool, sources } }: { trace: TraceState }) {
  return (
    <>
      {tool && (
        <span className="state">
          {sourceName(tool.name)} · {tool.summary}
        </span>
      )}
      <span className="pills">
        {Object.entries(sources).map(([name, { cached, count, failed }]) =>
          failed ? (
            <span key={name} className="pill fail">{sourceName(name)} ✕ failed</span>
          ) : cached ? (
            <span key={name} className="pill hollow">{sourceName(name)} · cached</span>
          ) : (
            <span key={name} className="pill fill">{sourceName(name)} {count}</span>
          ),
        )}
      </span>
    </>
  )
}

type Props = { step: Step; top: number; height: number; trace: TraceState; live: boolean; onJump: () => void }

export function TraceStep({ step, top, height, trace, live, onJump }: Props) {
  const t = trace.steps[step.id]
  const node = useRef<SVGGElement>(null)
  const animate = useAnimate()
  const prevStatus = usePrevious(t.status)
  const prevVisits = usePrevious(t.visits)
  const waiting = t.status === "waiting"

  useMotion(
    () => {
      const find = gsap.utils.selector(node)
      const origin = { transformOrigin: "50% 50%" }
      if (t.status === "active") {
        gsap.to(find(".arc"), { rotation: 360, duration: 0.9, ease: EASE.linear, repeat: -1, ...origin })
        gsap.fromTo(find(".ring"), { opacity: 0.55, scale: 1, ...origin }, { opacity: 0, scale: 1.04, duration: 1.3, ease: EASE.out, repeat: -1 })
      }
      if (waiting) gsap.fromTo(find(".ring"), { opacity: 0.6, scale: 1, ...origin }, { opacity: 0, scale: 1.05, duration: 2, ease: "sine.out", repeat: -1 })
      if (!animate || prevStatus === undefined) return
      if (prevStatus !== t.status && t.status === "done") gsap.from(find(".check"), { drawSVG: 0, duration: 0.35, ease: EASE.out })
      if (prevStatus !== t.status && t.status === "failed") gsap.from(node.current, { x: -3, duration: DUR.slow, ease: EASE.settle })
      if (prevVisits !== t.visits && t.visits > 1) gsap.from(find(".times"), { scale: 1.6, duration: 0.4, ease: EASE.pop, ...origin })
    },
    [t.status, t.visits],
    node,
  )
  const { done, total } = trace.extract
  const body = (
    <>
      <b>{step.label}</b>
      {t.visits > 1 && <span className="times"> ×{t.visits}</span>}
      <span className="state">{statusLine(step, t)}</span>
      {step.id === "search" && <Sources trace={trace} />}
      {step.id === "postings" && total > 0 && t.status !== "idle" && (
        <span className="state">
          <Bar value={done} max={total} label="Batches read" className="mini" /> {done} of {total} batches
        </span>
      )}
    </>
  )
  return (
    <g ref={node} role="listitem" className={`node ${t.status}${step.optional ? " optional" : ""}`} data-live={live || undefined}>
      <rect x={nodeX} y={top} width={nodeW} height={height} rx={10} />
      <Icon status={t.status} y={top} />
      <foreignObject x={nodeX} y={top} width={nodeW} height={height}>
        {/* A waiting Step takes you to the card that is waiting for you. */}
        {t.status === "waiting" ? (
          <button type="button" className="body" onClick={onJump}>{body}</button>
        ) : (
          <div className="body">{body}</div>
        )}
      </foreignObject>
    </g>
  )
}
