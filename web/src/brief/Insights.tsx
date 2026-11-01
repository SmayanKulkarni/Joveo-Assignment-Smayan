import { useState } from "react"
import type { Brief, Confidence } from "../api/types"
import { useMeta } from "../api/useMeta"
import { Cited } from "./Evidence"
import type { Ctx } from "./Evidence"

const FIRST = 6
const RANK: Confidence[] = ["high", "medium", "low"]
// A word and a meter each, so nothing rests on colour.
const METER: Record<Confidence, string> = { high: "●●●", medium: "●●○", low: "●○○" }

export function Insights({ insights, ctx }: { insights: Brief["insights"]; ctx: Ctx }) {
  const meta = useMeta()
  const [all, setAll] = useState(false)
  // Array.sort is stable, so equal confidence keeps the Brief's own order.
  const sorted = [...insights].sort((a, b) => RANK.indexOf(a.confidence) - RANK.indexOf(b.confidence))
  const shown = all ? sorted : sorted.slice(0, FIRST)

  return (
    <section>
      <h2>What we found</h2>
      {insights.length === 0 ? (
        <p>None: this Brief has no findings.</p>
      ) : (
        <>
          <ul className="ins">
            {shown.map((insight, i) => (
              <li key={i}>
                <span className={`pill ${insight.confidence}`}>
                  <span aria-hidden>{METER[insight.confidence]} </span>
                  {insight.confidence[0].toUpperCase() + insight.confidence.slice(1)} confidence
                </span>
                <p>{insight.text}</p>
                <details className="why">
                  <summary>Why this rating</summary>
                  <p>{insight.confidence_reason}</p>
                  <Cited cited={insight} ctx={ctx} />
                </details>
              </li>
            ))}
          </ul>
          {sorted.length > FIRST && !all && (
            <button type="button" onClick={() => setAll(true)}>
              Show all {sorted.length}
            </button>
          )}
          {meta && (
            <details>
              <summary>How confidence is rated</summary>
              <p>{meta.confidence_key}</p>
            </details>
          )}
        </>
      )}
    </section>
  )
}
