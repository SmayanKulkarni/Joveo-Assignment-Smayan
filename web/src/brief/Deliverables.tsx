import { useState } from "react"
import type { RunDetail } from "../api/types"
import { BriefView } from "./BriefView"
import { TABS } from "./documents"
import type { Document } from "./documents"
import { RecommendationView } from "./RecommendationView"

export function Deliverables({ id, detail }: { id: string; detail: RunDetail & { brief: NonNullable<RunDetail["brief"]> } }) {
  const [tab, setTab] = useState<Document>("brief")
  const { brief, recommendation, sample, glance } = detail
  return (
    <>
      <div role="tablist" className="tabs no-print">
        {TABS.map(({ key, label }) => (
          <button key={key} type="button" role="tab" aria-selected={tab === key} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>
      {tab === "brief" || !recommendation ? (
        <BriefView id={id} brief={brief} sample={sample} glance={glance} />
      ) : (
        <RecommendationView id={id} role={brief.hiring_request.role} recommendation={recommendation} ctx={{ stats: brief.stats.stats, sample }} />
      )}
    </>
  )
}
