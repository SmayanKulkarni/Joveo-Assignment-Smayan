import { useState } from "react"
import { ApiError } from "../api/client"

// What the card shows against itself: messages at the top, and plan errors under the field they name.
export type Refusal = { top: string[]; fields: Record<string, string> }
export type Send = (answer: object, record: string) => Promise<void>

function refusalOf(e: unknown): Refusal {
  const refusal: Refusal = { top: [], fields: {} }
  const errors = e instanceof ApiError ? e.errors : []
  for (const { loc, msg } of errors) {
    if (loc[0] === "plan" && loc.length > 1) refusal.fields[String(loc[1])] ??= msg
    else refusal.top.push(msg)
  }
  if (!refusal.top.length && !Object.keys(refusal.fields).length) refusal.top.push((e as Error).message)
  return refusal
}

// A refused answer keeps the card and its values, so the only state here is the busy flag and what was refused.
export function useSubmit(send: Send) {
  const [busy, setBusy] = useState(false)
  const [refusal, setRefusal] = useState<Refusal | null>(null)

  async function submit(answer: object, record: string) {
    setBusy(true)
    setRefusal(null)
    try {
      await send(answer, record)
    } catch (e) {
      setRefusal(refusalOf(e))
    }
    setBusy(false)
  }
  return { busy, refusal, submit }
}
