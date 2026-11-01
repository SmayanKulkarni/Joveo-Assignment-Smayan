import { useRef } from "react"
import type { Brief, Confidence, PostingRef } from "../api/types"
import { useMeta } from "../api/useMeta"
import { DUR, EASE, gsap, useAnimate, useMotion } from "../motion"
import { Evidence } from "./Evidence"
import { RunNotes } from "./RunNotes"

// The wording of brief/markdown.py, so screen, download and print agree.
const REPLAY_BANNER = "Replayed run: jobs data, LLM and Jev responses came from the replay cache, not live sources"
const NO_RECOMMENDATION = {
  job_title: "Not enough evidence to suggest a job title.",
  salary_band: "Not enough evidence to suggest a salary band.",
  top_skills: "Not enough evidence to suggest top skills.",
}
// A shape and a word each, so nothing rests on colour.
const METER: Record<Confidence, string> = { high: "●●●", medium: "●●○", low: "●○○" }
const OUTLOOK = {
  favourable: "▲ Favourable",
  competitive: "◆ Competitive",
  hard_to_fill: "▼ Hard to fill",
}

const money = (n: number) => n.toLocaleString("en-US", { maximumFractionDigits: 0 })

type Ctx = { brief: Brief; sample: PostingRef[] }

function Cited({ cited, ctx }: { cited: { stat_ids: string[]; evidence: Brief["outlook"]["evidence"] }; ctx: Ctx }) {
  return <Evidence evidence={cited.evidence} statIds={cited.stat_ids} stats={ctx.brief.stats.stats} sample={ctx.sample} />
}

function Recommendations({ ctx }: { ctx: Ctx }) {
  const { job_title, salary_band, top_skills } = ctx.brief.recommendations
  const rows = [
    ["Job title", job_title, job_title?.title, NO_RECOMMENDATION.job_title],
    ["Salary band", salary_band, salary_band && `${money(salary_band.low)} to ${money(salary_band.high)} ${salary_band.unit}`, NO_RECOMMENDATION.salary_band],
    ["Top skills", top_skills, top_skills?.skills.join(", "), NO_RECOMMENDATION.top_skills],
  ] as const
  return (
    <section>
      <h2>Client Recommendations</h2>
      <ul>
        {rows.map(([label, rec, value, missing]) => (
          <li key={label}>
            {rec ? (
              <>
                <b>{label}:</b> {value}. {rec.reason}
                <Cited cited={rec} ctx={ctx} />
              </>
            ) : (
              missing
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}

function Insights({ ctx }: { ctx: Ctx }) {
  const meta = useMeta()
  const { insights } = ctx.brief
  return (
    <section>
      <h2>Insights</h2>
      {insights.length === 0 ? (
        <p>None: this Brief has no findings.</p>
      ) : (
        <>
          {insights.map((insight, i) => (
            <article key={i} className="insight">
              <p>
                <span className={`pill ${insight.confidence}`}>
                  <span aria-hidden>{METER[insight.confidence]} </span>
                  {insight.confidence[0].toUpperCase() + insight.confidence.slice(1)}
                </span>{" "}
                {insight.text}
              </p>
              <p className="muted">{insight.confidence_reason}</p>
              <Cited cited={insight} ctx={ctx} />
            </article>
          ))}
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

function PostingsTable({ sample }: { sample: PostingRef[] }) {
  return (
    <details>
      <summary>Postings analysed ({sample.length})</summary>
      {sample.length === 0 ? (
        <p>None.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Company</th>
              <th>Link</th>
            </tr>
          </thead>
          <tbody>
            {sample.map((p) => (
              <tr key={p.key}>
                <td>{p.title}</td>
                <td>{p.company}</td>
                <td>
                  {p.url && (
                    <a href={p.url} target="_blank" rel="noopener noreferrer">
                      link
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </details>
  )
}

export function BriefView({ id, brief, sample }: { id: string; brief: Brief; sample: PostingRef[] }) {
  const ctx = { brief, sample }
  const article = useRef<HTMLElement>(null)
  const animate = useAnimate()
  useMotion(() => void (animate && gsap.from(article.current!.children, { y: 8, opacity: 0, duration: DUR.base, ease: EASE.out, stagger: 0.06 })), [], article)
  const target = brief.run_notes.final_plan.target_postings
  const { outlook, hiring_request: request } = brief

  return (
    <article ref={article} className="brief">
      <div className="brief-head">
        <h1>
          Market Brief: {request.role}, {request.location}
        </h1>
        <div className="actions no-print">
          <a href={`/api/runs/${id}/brief.json`} download>
            Download JSON
          </a>
          <a href={`/api/runs/${id}/brief.md`} download>
            Download Markdown
          </a>
          <button type="button" onClick={() => window.print()}>
            Print
          </button>
        </div>
      </div>
      {brief.replayed && <p className="notice">{REPLAY_BANNER}</p>}
      {brief.stats.sample_size < target && (
        <p className="notice">
          Weak Sample: {brief.stats.sample_size} Postings against a target of {target}. Treat this Brief as directional.
        </p>
      )}
      <section>
        <h2>Summary</h2>
        <p>{brief.summary}</p>
      </section>
      <section>
        <h2>Hiring Outlook</h2>
        <p className="outlook">{OUTLOOK[outlook.rating]}</p>
        <p>{outlook.reason}</p>
        {/* The default rests on no Stats, so it has no Evidence to show. */}
        {outlook.stat_ids.length > 0 && <Cited cited={outlook} ctx={ctx} />}
      </section>
      <Recommendations ctx={ctx} />
      <Insights ctx={ctx} />
      <RunNotes notes={brief.run_notes} />
      <PostingsTable sample={sample} />
    </article>
  )
}
