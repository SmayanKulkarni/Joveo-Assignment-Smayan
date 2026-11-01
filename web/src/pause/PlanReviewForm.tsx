import { useState } from "react"
import type { SearchPlan } from "../api/types"
import { useMeta } from "../api/useMeta"
import { categoryName } from "../labels"
import { searchCost, where } from "../util"
import { AbortButton, Refusals } from "./parts"
import { PlanEditor } from "./PlanEditor"
import { useSubmit } from "./submit"
import type { Send } from "./submit"

type Assumption = { about: string; value: string; reason: string }

// Mounted only while editing, so cancelling drops whatever the server refused.
function EditPlan({ plan, send, onCancel }: { plan: SearchPlan; send: Send; onCancel: () => void }) {
  const meta = useMeta()
  const { busy, refusal, submit } = useSubmit(send)
  if (!meta) return null
  return (
    <PlanEditor
      plan={plan}
      countries={meta.countries}
      categories={meta.categories}
      busy={busy}
      refusal={refusal}
      onUse={(edited) => submit({ action: "edit", plan: edited, feedback: null }, "You edited the plan")}
      onCancel={onCancel}
    />
  )
}

export function PlanReviewForm({ plan, assumptions, callsLeft, send }: { plan: SearchPlan; assumptions: Assumption[]; callsLeft: number | null; send: Send }) {
  const [mode, setMode] = useState<"read" | "edit" | "reject">("read")
  const [feedback, setFeedback] = useState("")
  const { busy, refusal, submit } = useSubmit(send)

  if (mode === "edit") return <EditPlan plan={plan} send={send} onCancel={() => setMode("read")} />

  return (
    <section className="card">
      <h2>Check the search plan</h2>
      <dl className="plan">
        <dt>Titles</dt>
        <dd className="chips">
          {plan.titles.map((title) => (
            <span key={title} className="chip">
              {title}
            </span>
          ))}
        </dd>
        <dt>Where</dt>
        <dd>{where(plan)}</dd>
        <dt>Radius</dt>
        <dd>{plan.radius_km} km</dd>
        <dt>Posted within</dt>
        <dd>{plan.max_days_old} days</dd>
        <dt>Target</dt>
        <dd>{plan.target_postings} Postings</dd>
        <dt>Category</dt>
        <dd>{plan.category ? categoryName(plan.category) : "Any"}</dd>
      </dl>
      <p className="muted">
        {searchCost(plan)}.{callsLeft !== null && ` ${callsLeft} Adzuna calls left today.`}
      </p>
      {assumptions.length > 0 && (
        <>
          <h3>Assumptions</h3>
          <ul>
            {assumptions.map((a) => (
              <li key={a.about}>
                {a.about}: {a.value}, because {a.reason}
              </li>
            ))}
          </ul>
        </>
      )}
      {mode === "reject" && (
        <label>
          What should the next plan do differently?
          <textarea value={feedback} onChange={(e) => setFeedback(e.target.value)} rows={3} />
        </label>
      )}
      <Refusals refusal={refusal} />
      <div className="actions">
        {mode === "read" ? (
          <>
            <button type="button" className="start" disabled={busy} onClick={() => submit({ action: "approve", plan: null, feedback: null }, "You approved the plan")}>
              Approve
            </button>
            <button type="button" disabled={busy} onClick={() => setMode("edit")}>
              Edit
            </button>
            <button type="button" disabled={busy} onClick={() => setMode("reject")}>
              Ask for a different plan
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              className="start"
              disabled={busy || !feedback.trim()}
              onClick={() => submit({ action: "reject", plan: null, feedback: feedback.trim() }, "You asked for a different plan")}
            >
              Send feedback
            </button>
            <button type="button" disabled={busy} onClick={() => setMode("read")}>
              Back
            </button>
          </>
        )}
        <AbortButton busy={busy} onConfirm={() => submit({ action: "abort", plan: null, feedback: null }, "You aborted the Run")} />
      </div>
    </section>
  )
}
