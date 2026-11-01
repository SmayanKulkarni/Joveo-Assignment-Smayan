import { useId, useState } from "react"
import type { Question } from "../api/types"
import { plural } from "../util"
import { Refusals } from "./parts"
import { useSubmit } from "./submit"
import type { Send } from "./submit"

export function ClarifyForm({ questions, send }: { questions: Question[]; send: Send }) {
  const [answers, setAnswers] = useState(() => questions.map(() => ""))
  const { busy, refusal, submit } = useSubmit(send)
  const group = useId()
  const filled = answers.filter((a) => a.trim()).length

  const set = (i: number, value: string) => setAnswers((all) => all.map((a, j) => (j === i ? value : a)))
  // A place question takes several areas, kept as one string joined with ", ".
  const picked = (i: number) => answers[i].split(",").map((a) => a.trim()).filter(Boolean)
  const toggle = (i: number, option: string) => {
    const now = picked(i)
    set(i, (now.includes(option) ? now.filter((a) => a !== option) : [...now, option]).join(", "))
  }

  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault()
        // Blank is a skip, and the answers stay in question order.
        submit({ answers: answers.map((a) => a.trim()) }, filled ? `You answered ${plural(filled, "question")}` : "You skipped the questions")
      }}
    >
      <h2>{questions.length === 1 ? "A quick question" : "A few quick questions"}</h2>
      {questions.map((q, i) => (
        <fieldset key={i}>
          <legend>{q.text}</legend>
          {q.options.length > 0 && (
            <div className="chips">
              {/* Picking a chip fills the box, and typing changes the value so the chip clears. */}
              {q.options.map((option) =>
                q.about === "location" ? (
                  <label key={option} className="chip choice">
                    <input type="checkbox" checked={picked(i).includes(option)} onChange={() => toggle(i, option)} />
                    {option}
                  </label>
                ) : (
                  <label key={option} className="chip choice">
                    <input type="radio" name={`${group}-${i}`} checked={answers[i] === option} onChange={() => set(i, option)} />
                    {option}
                  </label>
                ),
              )}
            </div>
          )}
          <input
            type="text"
            value={answers[i]}
            onChange={(e) => set(i, e.target.value)}
            aria-label={`Your answer to: ${q.text}`}
            placeholder="Or type your own"
          />
        </fieldset>
      ))}
      <Refusals refusal={refusal} />
      <div className="actions">
        <button type="submit" className="start" disabled={busy}>
          {filled ? "Send answers" : "Continue without answering"}
        </button>
      </div>
    </form>
  )
}
