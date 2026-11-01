import { useState } from "react"
import type { Pause } from "../api/types"
import { planLine, plural } from "../util"
import { AbortButton, Refusals } from "./parts"
import { useSubmit } from "./submit"
import type { Send } from "./submit"

type Payload = Extract<Pause, { kind: "low_data_review" }>["payload"]

export function LowDataForm({ payload, send }: { payload: Payload; send: Send }) {
  const [guidance, setGuidance] = useState("")
  const [wholeCountry, setWholeCountry] = useState(false)
  const { busy, refusal, submit } = useSubmit(send)
  const { count, target, fetched, rejected, attempts, blocked, calls_left, plans } = payload
  const hasPlace = plans[plans.length - 1].locations.length > 0

  return (
    <section className="card">
      <h2>Too few Postings</h2>
      <p>
        Only {plural(count, "relevant Posting")} found; the target is {target}.
      </p>
      <p>
        Fetched {fetched}, rejected {rejected} as not the role, over {plural(attempts, "Attempt")}.
      </p>
      {blocked && <p className="refusal">{blocked}</p>}
      {calls_left !== null && <p>Adzuna calls left: {calls_left}</p>}
      <details>
        <summary>Plans tried ({plans.length})</summary>
        <ol>
          {plans.map((plan, i) => (
            <li key={i}>{planLine(plan)}</li>
          ))}
        </ol>
      </details>
      <label>
        Guidance for a wider search (optional)
        <textarea value={guidance} onChange={(e) => setGuidance(e.target.value)} rows={2} />
      </label>
      {hasPlace && (
        <label className="check">
          <input type="checkbox" checked={wholeCountry} onChange={(e) => setWholeCountry(e.target.checked)} /> Search the whole country
        </label>
      )}
      <Refusals refusal={refusal} />
      <div className="actions">
        <button
          type="button"
          className="start"
          disabled={busy}
          onClick={() => submit({ action: "broaden", guidance: guidance.trim() || null, whole_country: hasPlace && wholeCountry }, "You asked for a wider search")}
        >
          Search wider
        </button>
        <button type="button" disabled={busy} onClick={() => submit({ action: "continue", guidance: null }, `You continued with ${plural(count, "Posting")}`)}>
          Continue with {plural(count, "Posting")}
        </button>
        <AbortButton busy={busy} onConfirm={() => submit({ action: "abort", guidance: null }, "You aborted the Run")} />
      </div>
    </section>
  )
}
