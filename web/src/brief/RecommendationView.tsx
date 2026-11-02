import type { Recommendation } from "../api/types"
import { downloadUrl } from "./documents"
import type { Ctx } from "./Evidence"
import { Tile } from "./Tiles"

const money = (n: number) => n.toLocaleString("en-US", { maximumFractionDigits: 0 })

type Props = { id: string; role: string; recommendation: Recommendation; ctx: Ctx }

export function RecommendationView({ id, role, recommendation: r, ctx }: Props) {
  const band = r.salary_band
  return (
    <article className="brief">
      <div className="brief-head">
        <h1>Customer Recommendation: {role}</h1>
        <div className="actions no-print">
          <a href={downloadUrl(id, "recommendation", "json")} download>
            Download JSON
          </a>
          <a href={downloadUrl(id, "recommendation", "md")} download>
            Download Markdown
          </a>
          <button type="button" onClick={() => window.print()}>
            Print
          </button>
        </div>
      </div>
      <div className="tiles">
        <Tile label="Job title to aim for" value={r.job_title?.title} cites={r.job_title} ctx={ctx} />
        <Tile label="Salary band" value={band ? `${money(band.low)} to ${money(band.high)}` : undefined} unit={band?.unit} cites={band} ctx={ctx} />
        <Tile label="Top skills" value={r.top_skills?.skills.join(", ")} cites={r.top_skills} ctx={ctx} />
      </div>
      <section>
        <h2>Matches</h2>
        <p>{r.matches_note}</p>
      </section>
    </article>
  )
}
