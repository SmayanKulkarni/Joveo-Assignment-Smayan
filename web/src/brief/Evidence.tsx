import { useState } from "react"
import type { Evidence as EvidenceData, PostingRef, Stat } from "../api/types"
import { plural } from "../util"

const FIRST = 10

const formatValue = (value: number | string) =>
  typeof value === "number" ? value.toLocaleString("en-US", { maximumFractionDigits: 2 }) : value

type Props = { evidence: EvidenceData; statIds: string[]; stats: Stat[]; sample: PostingRef[]; open?: boolean }

export type Ctx = { stats: Stat[]; sample: PostingRef[] }

// Anything that cites Stats and Postings: a tile, an Insight or a chart row.
export const Cited = ({ cited, ctx }: { cited: { stat_ids: string[]; evidence: EvidenceData }; ctx: Ctx }) => (
  <Evidence evidence={cited.evidence} statIds={cited.stat_ids} stats={ctx.stats} sample={ctx.sample} />
)

export function Evidence({ evidence, statIds, stats, sample, open }: Props) {
  const [all, setAll] = useState(false)
  const keys = evidence.posting_keys
  const byKey = new Map(sample.map((p) => [p.key, p]))
  const cited = stats.filter((s) => statIds.includes(s.id))
  const shown = all ? keys : keys.slice(0, FIRST)

  return (
    <details className="evidence" open={open}>
      <summary>Evidence: {plural(keys.length, "Posting")}</summary>
      {cited.length > 0 && (
        <ul>
          {cited.map((s) => (
            <li key={s.id}>
              {s.label}: {formatValue(s.value)}
              {s.unit && ` ${s.unit}`}
            </li>
          ))}
        </ul>
      )}
      <ul>
        {shown.map((key) => {
          const p = byKey.get(key)
          return (
            <li key={key}>
              {p ? `${p.title}${p.company ? `, ${p.company}` : ""}` : key}
              {p?.url && (
                <>
                  {" "}
                  <a href={p.url} target="_blank" rel="noopener noreferrer">
                    link
                  </a>
                </>
              )}
            </li>
          )
        })}
      </ul>
      {keys.length > FIRST && !all && (
        <button type="button" onClick={() => setAll(true)}>
          Show all {keys.length}
        </button>
      )}
    </details>
  )
}
