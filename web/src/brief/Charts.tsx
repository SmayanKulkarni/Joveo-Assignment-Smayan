import { useState } from "react"
import type { Glance, Row, RowChart } from "../api/types"
import { Evidence } from "./Evidence"
import type { Ctx } from "./Evidence"

const money = (n: number) => n.toLocaleString("en-US", { maximumFractionDigits: 0 })

function Bars({ chart, ctx, title }: { chart: RowChart; ctx: Ctx; title: string }) {
  const [open, setOpen] = useState<string | null>(null)
  const max = Math.max(...chart.rows.map((r) => r.count))
  const hasRequired = chart.rows.some((r) => r.required)
  const share = (n: number) => `${(n / max) * 100}%`

  return (
    <section className="tile">
      <h3>{title}</h3>
      {chart.rows.map((row: Row) => {
        const rest = row.count - (row.required ?? 0)
        return (
          <div key={row.label}>
            <button
              type="button"
              className="bar-row"
              aria-expanded={open === row.label}
              title={`${row.label}: ${row.count}. Click for the evidence.`}
              onClick={() => setOpen(open === row.label ? null : row.label)}
            >
              <span>{row.label}</span>
              <span className="track" aria-hidden>
                {row.required ? <i className="must" style={{ width: share(row.required) }} /> : null}
                {rest > 0 && <i className={row.required ? "other" : ""} style={{ width: share(rest) }} />}
              </span>
              <span className="num">{row.count}</span>
            </button>
            {open === row.label && <Evidence open evidence={row.evidence} statIds={row.stat_ids} stats={ctx.stats} sample={ctx.sample} />}
          </div>
        )
      })}
      <p className="muted">
        {chart.caption}
        {hasRequired && " Dark is required, light is the rest."}
      </p>
    </section>
  )
}

function Pay({ pay, ctx }: { pay: NonNullable<Glance["pay"]>; ctx: Ctx }) {
  const at = (v: number) => `${(v / (pay.high * 1.15)) * 100}%`
  return (
    <section className="tile">
      <h3>Typical pay</h3>
      <div className="range" aria-hidden>
        <div className="line" />
        <div className="box" style={{ left: at(pay.low), width: `calc(${at(pay.high)} - ${at(pay.low)})` }} />
        <div className="med" style={{ left: at(pay.median) }} />
        <span style={{ left: at(pay.low), top: -16 }}>{money(pay.low)}</span>
        <span style={{ left: at(pay.high), top: 28, transform: "translateX(-100%)" }}>{money(pay.high)}</span>
      </div>
      <p className="muted">
        Half of the {pay.postings} postings that list pay fall inside the green bar. The dark line is the midpoint, {money(pay.median)} {pay.unit}.
      </p>
      <Evidence evidence={pay.evidence} statIds={pay.stat_ids} stats={ctx.stats} sample={ctx.sample} />
    </section>
  )
}

export function Charts({ glance, ctx }: { glance: Glance; ctx: Ctx }) {
  const { pay, skills, places, employers } = glance
  if (!pay && !skills && !places && !employers) return null
  return (
    <div className="charts">
      {pay && <Pay pay={pay} ctx={ctx} />}
      {skills && <Bars chart={skills} ctx={ctx} title="Skills employers ask for" />}
      {places && <Bars chart={places} ctx={ctx} title="Where the postings are" />}
      {employers && <Bars chart={employers} ctx={ctx} title="Who is hiring most" />}
    </div>
  )
}
