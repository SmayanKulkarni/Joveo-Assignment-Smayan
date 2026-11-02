import type { Brief } from "../api/types"
import { useMeta } from "../api/useMeta"
import { Cited } from "./Evidence"
import type { Ctx } from "./Evidence"

// A shape and a word, so nothing rests on colour.
const OUTLOOK = { favourable: "▲ Favourable", competitive: "◆ Competitive", hard_to_fill: "▼ Hard to fill" }
const NONE = "Not enough evidence"

type Cites = { reason: string; stat_ids: string[]; evidence: Brief["outlook"]["evidence"] }

export function Tile({ label, value, unit, cites, ctx, tone, meaning }: { label: string; value?: string; unit?: string; cites?: Cites | null; ctx: Ctx; tone?: string; meaning?: string }) {
  return (
    <div className={`tile hero ${tone ?? ""}`}>
      <small>{label}</small>
      {value ? <b>{value}</b> : <b className="muted">{NONE}</b>}
      {value && unit && <span className="muted">{unit}</span>}
      {meaning && <p>{meaning}</p>}
      {cites && <p className="reason">{cites.reason}</p>}
      {/* The default Outlook rests on no Stats, so it has no Evidence to show. */}
      {cites && cites.stat_ids.length > 0 && <Cited cited={cites} ctx={ctx} />}
    </div>
  )
}

export function Tiles({ brief, ctx }: { brief: Brief; ctx: Ctx }) {
  const { outlook } = brief
  const meaning = useMeta()?.outlook_meaning[outlook.rating]
  return (
    <div className="tiles">
      <Tile label="Hiring outlook" value={OUTLOOK[outlook.rating]} cites={outlook} ctx={ctx} tone={outlook.rating} meaning={meaning} />
    </div>
  )
}
