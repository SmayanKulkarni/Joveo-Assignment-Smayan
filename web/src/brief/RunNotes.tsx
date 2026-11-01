import type { Brief } from "../api/types"
import { planLine } from "../util"

// Source names as the Markdown prints them; an unknown source shows raw.
const SOURCES: Record<string, string> = { adzuna: "Adzuna", usajobs: "USAJOBS" }

function bySource(keys: string[]) {
  const counts = new Map<string, number>()
  for (const key of keys) {
    const source = key.split(":")[0]
    counts.set(source, (counts.get(source) ?? 0) + 1)
  }
  return [...counts].sort().map(([source, n]) => `${SOURCES[source] ?? source} ${n}`)
}

function Item({ label, lines, empty }: { label: string; lines: string[]; empty: string }) {
  return (
    <li>
      <b>{label}:</b>
      {lines.length === 0 ? (
        ` ${empty}`
      ) : (
        <ul>
          {lines.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      )}
    </li>
  )
}

export function RunNotes({ notes }: { notes: Brief["run_notes"] }) {
  const sources = bySource(notes.postings_analysed.posting_keys)
  const analysed = `${notes.postings_analysed.posting_keys.length}${sources.length ? ` (${sources.join(", ")})` : ""}`

  return (
    <section>
      <h2>Run Notes</h2>
      <ul className="notes">
        <li>
          <b>Caveats:</b>
          {notes.caveats.length === 0 ? (
            " None"
          ) : (
            <ul>
              {notes.caveats.map((caveat) => (
                <li key={caveat}>
                  <span aria-hidden>⚠ </span>
                  <b>Caveat</b> {caveat}
                </li>
              ))}
            </ul>
          )}
        </li>
        <Item label="Questions and answers" lines={notes.questions.map((q) => `${q.text} → ${q.answer || "no answer"}`)} empty="None asked" />
        <Item label="Assumptions" lines={notes.assumptions.map((a) => `${a.about}: ${a.value} (${a.reason})`)} empty="None" />
        <li>
          <b>Focus:</b> {notes.focus.join(", ") || "All Dimensions"}
        </li>
        <li>
          <b>Final search plan:</b> {planLine(notes.final_plan)}
        </li>
        {notes.earlier_plans.length > 0 && <Item label="Earlier search plans" lines={notes.earlier_plans.map(planLine)} empty="" />}
        <li>
          <b>Postings analysed:</b> {analysed}
        </li>
        <Item label="Source match counts" lines={notes.match_totals} empty="None" />
        {notes.attribution && <li>{notes.attribution}</li>}
      </ul>
    </section>
  )
}
