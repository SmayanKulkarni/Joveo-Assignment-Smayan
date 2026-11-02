import { uploadResume } from "../api/client"
import type { ResumeInfo } from "../api/types"

export type Upload = { startedAt: number; result: ResumeInfo | null; error: unknown }

const EVENT = "resume-upload"
// How long after a reload an upload can still be finishing on the server: the read takes about 20 s, the model can retry.
const RELOAD_WINDOW_MS = 120_000
const live = new Map<string, Upload>()
const key = (id: string) => `resume-upload:${id}`

// Kept outside the component, so leaving the page doesn't drop an upload the server is still reading.
export function startUpload(id: string, body: Blob | string) {
  const upload: Upload = { startedAt: Date.now(), result: null, error: null }
  live.set(id, upload)
  // sessionStorage covers a reload, which loses this module's memory but not the server's work.
  try {
    sessionStorage.setItem(key(id), String(upload.startedAt))
  } catch {
    // No storage, so a reload just won't know to check.
  }
  uploadResume(id, body)
    .then((result) => (upload.result = result), (error) => (upload.error = error ?? new Error("upload failed")))
    .finally(() => {
      forgetReload(id)
      dispatchEvent(new CustomEvent(EVENT, { detail: id }))
    })
}

export const uploadOf = (id: string) => live.get(id)

export const finishUpload = (id: string) => live.delete(id)

export function onUploadSettled(id: string, fn: () => void) {
  const handler = (event: Event) => (event as CustomEvent).detail === id && fn()
  addEventListener(EVENT, handler)
  return () => removeEventListener(EVENT, handler)
}

// When an upload was started before a reload and may still be running on the server.
export function reloadedUpload(id: string): number | null {
  try {
    const startedAt = Number(sessionStorage.getItem(key(id)))
    return startedAt && !live.has(id) ? startedAt : null
  } catch {
    return null
  }
}

export const reloadWindowOver = (startedAt: number) => Date.now() - startedAt > RELOAD_WINDOW_MS

export function forgetReload(id: string) {
  try {
    sessionStorage.removeItem(key(id))
  } catch {
    // Nothing was stored.
  }
}
