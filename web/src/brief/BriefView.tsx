import { useRef } from "react"
import { API } from "../api/client"
import type { Brief, Glance, PostingRef } from "../api/types"
import { DUR, EASE, gsap, useAnimate, useMotion } from "../motion"
import { Charts } from "./Charts"
import { Insights } from "./Insights"
import { RunNotes } from "./RunNotes"
import { Tiles } from "./Tiles"

// The wording of brief/markdown.py, so screen, download and print agree.
const REPLAY_BANNER = "Replayed run: jobs data, LLM and Jev responses came from the replay cache, not live sources"

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

type Props = { id: string; brief: Brief; sample: PostingRef[]; glance: Glance | null }

export function BriefView({ id, brief, sample, glance }: Props) {
  const ctx = { stats: brief.stats.stats, sample }
  const article = useRef<HTMLElement>(null)
  const animate = useAnimate()
  useMotion(() => void (animate && gsap.from(article.current!.children, { y: 8, opacity: 0, duration: DUR.base, ease: EASE.out, stagger: 0.06 })), [], article)
  const { hiring_request: request } = brief

  return (
    <article ref={article} className="brief">
      <div className="brief-head">
        <h1>
          Market Brief: {request.role}, {request.location}
        </h1>
        <div className="actions no-print">
          <a href={`${API}/runs/${id}/brief.json`} download>
            Download JSON
          </a>
          <a href={`${API}/runs/${id}/brief.md`} download>
            Download Markdown
          </a>
          <button type="button" onClick={() => window.print()}>
            Print
          </button>
        </div>
      </div>
      <Tiles brief={brief} ctx={ctx} />
      <div>
        {brief.replayed && <p className="notice">{REPLAY_BANNER}</p>}
        {/* The Weak Sample notice is one of these, so it never shows twice. */}
        {glance?.reader_notes.map((note) => (
          <p key={note} className="note">
            <span aria-hidden>⚠ </span>
            {note}
          </p>
        ))}
      </div>
      <section>
        <h2>Summary</h2>
        <p>{brief.summary}</p>
      </section>
      {glance && <Charts glance={glance} ctx={ctx} />}
      <Insights insights={brief.insights} ctx={ctx} />
      <details className="researched">
        <summary>How this was researched</summary>
        <RunNotes notes={brief.run_notes} />
        <PostingsTable sample={sample} />
      </details>
      {brief.run_notes.attribution && <footer className="muted">{brief.run_notes.attribution}</footer>}
    </article>
  )
}
