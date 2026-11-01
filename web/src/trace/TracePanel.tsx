import { useEffect, useRef } from "react"
import { EASE, gsap, useAnimate, useMotion, usePrevious } from "../motion"
import type { Graph } from "../api/types"
import { backEdges, bandsOf, stepIndex } from "../run/steps"
import type { TraceState } from "../run/trace"
import { ProgressBar } from "./ProgressBar"
import { GEOMETRY, TraceStep } from "./TraceStep"

const { railX, nodeX, nodeW, iconY, iconR } = GEOMETRY
const WIDTH = 284
const GAP = 22
const BAND_H = 26
// Search holds the source pills, and Read postings holds its bar.
const heightOf = (id: string) => (id === "search" ? 96 : id === "postings" ? 66 : 48)

export function TracePanel({ trace, graph, onJump }: { trace: TraceState; graph: Graph; onJump: () => void }) {
  const svg = useRef<SVGSVGElement>(null)

  let y = 0
  const labels: { name: string; y: number }[] = []
  const rows = bandsOf(graph).flatMap(({ name, steps }) => {
    labels.push({ name, y: y + 16 })
    y += BAND_H
    return steps.map((step) => {
      const row = { step, top: y, height: heightOf(step.id) }
      y += row.height + GAP
      return row
    })
  })
  const animate = useAnimate()
  const loops = usePrevious(trace.loops)
  const liveStep = trace.current && trace.steps[trace.current].status === "active" ? trace.current : null
  const centre = (id: string) => rows[stepIndex(id)].top + iconY

  useMotion(
    () => {
      // The rail leaving the live Step flows; the dashes are CSS, the tween only slides them.
      gsap.fromTo(".rail.active", { strokeDashoffset: 10 }, { strokeDashoffset: 0, duration: 0.6, ease: EASE.linear, repeat: -1 })
      // One dot per batch, on the newest back-edge.
      const edge = trace.lastLoop
      if (!animate || loops === undefined || !edge || trace.loops <= loops) return
      gsap.fromTo(
        ".dot",
        { opacity: 1 },
        { motionPath: { path: `[data-edge="${edge}"]`, align: `[data-edge="${edge}"]`, alignOrigin: [0.5, 0.5] }, duration: 0.9, ease: "power1.inOut", onComplete: () => void gsap.set(".dot", { opacity: 0 }) },
      )
    },
    [liveStep, trace.loops],
    svg,
  )

  // The live Step stays in view as the Run moves down the rail.
  useEffect(() => {
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches
    svg.current?.querySelector("[data-live]")?.scrollIntoView({ block: "nearest", behavior: reduced ? "auto" : "smooth" })
  }, [trace.current])

  return (
    <aside className="trace" aria-label="Run progress">
      <ProgressBar trace={trace} />
      <svg ref={svg} viewBox={`0 0 ${WIDTH} ${y - GAP}`} width={WIDTH} role="list" aria-label="Steps">
        <defs>
          {["", "taken"].map((kind) => (
            <marker key={kind} id={`arrow${kind}`} className={kind} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0 0 L8 4 L0 8 z" />
            </marker>
          ))}
        </defs>
        {labels.map(({ name, y }) => (
          <text key={name} className="band" x={nodeX} y={y}>{name}</text>
        ))}
        {rows.slice(0, -1).map(({ step }, i) => (
          <line
            key={step.id}
            className={`rail ${trace.steps[step.id].status}`}
            x1={railX}
            x2={railX}
            y1={centre(step.id) + iconR}
            y2={centre(rows[i + 1].step.id) - iconR}
          />
        ))}
        {backEdges(graph).map((edge) => {
          const [from, to] = edge.split("→")
          const bow = 14 + 8 * (stepIndex(from) - stepIndex(to))
          const x = nodeX + nodeW
          const taken = trace.looped.includes(edge)
          return (
            <path
              key={edge}
              data-edge={edge}
              className={`back${taken ? " taken" : ""}`}
              d={`M${x} ${centre(from)} C${x + bow} ${centre(from)} ${x + bow} ${centre(to)} ${x + 5} ${centre(to)}`}
              markerEnd={`url(#arrow${taken ? "taken" : ""})`}
            />
          )
        })}
        <circle className="dot" r={3.5} />
        {rows.map(({ step, top, height }) => (
          <TraceStep key={step.id} step={step} top={top} height={height} trace={trace} live={step.id === trace.current} onJump={onJump} />
        ))}
      </svg>
    </aside>
  )
}
