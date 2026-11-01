import type { Brief } from "../api/types"
import { Cited } from "./Evidence"
import type { Ctx } from "./Evidence"

// A shape and a word, so nothing rests on colour.
const OUTLOOK = { favourable: "▲ Favourable", competitive: "◆ Competitive", hard_to_fill: "▼ Hard to fill" }
const NONE = "Not enough evidence"
const money = (n: number) => n.toLocaleString("en-US", { maximumFractionDigits: 0 })

type Cites = { reason: string; stat_ids: string[]; evidence: Brief["outlook"]["evidence"] }

function Tile({ label, value, unit, cites, ctx }: { label: string; value?: string; unit?: string; cites?: Cites | null; ctx: Ctx }) {
  return (
    <div className="tile">
      <small>{label}</small>
      {value ? <b>{value}</b> : <b className="muted">{NONE}</b>}
      {value && unit && <span className="muted">{unit}</span>}
      {cites && (
        <details className="why">
          <summary>Why</summary>
          <p>{cites.reason}</p>
          {/* The default Outlook rests on no Stats, so it has no Evidence to show. */}
          {cites.stat_ids.length > 0 && <Cited cited={cites} ctx={ctx} />}
        </details>
      )}
    </div>
  )
}

export function Tiles({ brief, ctx }: { brief: Brief; ctx: Ctx }) {
  const { outlook, recommendations: r } = brief
  const band = r.salary_band
  return (
    <div className="tiles">
      <Tile label="Hiring outlook" value={OUTLOOK[outlook.rating]} cites={outlook} ctx={ctx} />
      <Tile label="Job title" value={r.job_title?.title} cites={r.job_title} ctx={ctx} />
      <Tile label="Salary band" value={band ? `${money(band.low)} to ${money(band.high)}` : undefined} unit={band?.unit} cites={band} ctx={ctx} />
      <Tile label="Top skills" value={r.top_skills?.skills.slice(0, 4).join(", ")} cites={r.top_skills} ctx={ctx} />
    </div>
  )
}
