import type { Brief } from "../api/types"
import { planLine } from "../util"

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
  return (
    <section>
      <ul className="notes">
        <Item label="Things to keep in mind" lines={notes.caveats.map((c) => `⚠ ${c}`)} empty="None" />
        <Item label="Questions and answers" lines={notes.questions.map((q) => `${q.text} → ${q.answer || "no answer"}`)} empty="None asked" />
        <Item label="Assumptions" lines={notes.assumptions.map((a) => `${a.about}: ${a.value} (${a.reason})`)} empty="None" />
        <li>
          <b>Search used:</b> {planLine(notes.final_plan)}
        </li>
        {notes.earlier_plans.length > 0 && <Item label="Earlier searches" lines={notes.earlier_plans.map(planLine)} empty="" />}
        <li>
          <b>Postings analysed:</b> {notes.postings_analysed.posting_keys.length}
        </li>
      </ul>
    </section>
  )
}
