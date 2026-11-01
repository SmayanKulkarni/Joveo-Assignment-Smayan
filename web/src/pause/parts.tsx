import { useState } from "react"
import type { Refusal } from "./submit"

export function Refusals({ refusal }: { refusal: Refusal | null }) {
  if (!refusal?.top.length) return null
  return (
    <div className="refusal" role="alert">
      {refusal.top.map((message) => (
        <p key={message}>{message}</p>
      ))}
    </div>
  )
}

// Abort is the one irreversible answer, so it asks first.
export function AbortButton({ busy, onConfirm }: { busy: boolean; onConfirm: () => void }) {
  const [asking, setAsking] = useState(false)
  if (!asking) {
    return (
      <button type="button" className="danger" disabled={busy} onClick={() => setAsking(true)}>
        Abort
      </button>
    )
  }
  return (
    <span className="confirm" role="group" aria-label="Confirm abort">
      Abort this Run?
      <button type="button" className="danger" disabled={busy} onClick={onConfirm}>
        Yes
      </button>
      <button type="button" disabled={busy} onClick={() => setAsking(false)}>
        No
      </button>
    </span>
  )
}
