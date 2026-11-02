import { useState } from "react"
import type { Match, PostingRef, Recommendation } from "../api/types"
import { downloadUrl } from "./documents"
import type { Ctx } from "./Evidence"
import { Tile } from "./Tiles"

const money = (n: number) => n.toLocaleString("en-US", { maximumFractionDigits: 0 })

const LEVELS = { fits: "Fits", stretch: "Stretch", far: "Far", not_judged: "Not judged" }

function MatchRow({ rank, match, posting }: { rank: number; match: Match; posting: PostingRef }) {
  // Both spellings when they differ, as in the download.
  const skill = (s: Match["matched"][number]) =>
    (s.posting.toLowerCase() === s.resume.toLowerCase() ? s.posting : `${s.posting} (Resume: ${s.resume})`) + (s.added ? " [added by CSM]" : "")
  return (
    <li className="match">
      <strong>
        {rank}. {posting.title}
      </strong>
      , {[posting.company, posting.location].filter(Boolean).join(", ")}
      <ul>
        <li>Pay: {posting.pay}</li>
        <li>
          Score {match.score}, {LEVELS[match.level]} ({match.level_reason})
        </li>
        <li>Matched: {match.matched.map(skill).join(", ") || "none"}</li>
        <li>Missing: {match.missing.join(", ") || "none"}</li>
        <li>
          Source: {posting.source}. {posting.labels.map((l) => `${l}. `)}
          {posting.url && (
            <a href={posting.url} target="_blank" rel="noopener noreferrer">
              link
            </a>
          )}
        </li>
      </ul>
    </li>
  )
}

type Props = { id: string; role: string; recommendation: Recommendation; matches: Match[]; shownKeys: string[]; ctx: Ctx }

export function RecommendationView({ id, role, recommendation: r, matches, shownKeys, ctx }: Props) {
  const [all, setAll] = useState(false)
  const band = r.salary_band
  const byKey = new Map(ctx.sample.map((p) => [p.key, p]))
  // A Match whose Posting isn't in the Sample can't be shown, so it is left out.
  const listed = matches.filter((m) => byKey.has(m.posting_key))
  const top = listed.filter((m) => shownKeys.includes(m.posting_key))
  const rest = listed.filter((m) => !shownKeys.includes(m.posting_key))
  const rows = all ? [...top, ...rest] : top
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
      {r.compared && <p>{r.compared}</p>}
      <section>
        <h2>Matches</h2>
        {top.length === 0 && <p>{r.matches_note}</p>}
        <ol className="matches">
          {rows.map((m, i) => (
            <MatchRow key={m.posting_key} rank={i + 1} match={m} posting={byKey.get(m.posting_key)!} />
          ))}
        </ol>
        {rest.length > 0 && !all && (
          <button type="button" className="no-print" onClick={() => setAll(true)}>
            Show the other {rest.length}
          </button>
        )}
      </section>
    </article>
  )
}
