import type { Dimension, Meta, RunDetail } from "./types"

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly errors: { loc: (string | number)[]; msg: string }[] = [],
  ) {
    super(message)
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init)
  if (response.ok) return response.json()
  // Refusals carry {code, message}; anything else (a proxy error, say) still becomes an ApiError.
  const body = await response.json().catch(() => ({}))
  throw new ApiError(response.status, body.code ?? "unknown", body.message ?? response.statusText, body.errors)
}

export const startRun = (request_text: string, focus: Dimension[]) =>
  call<{ thread_id: string }>("/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request_text, focus }),
  })

export const getRun = (id: string) => call<RunDetail>(`/runs/${id}`)

export const getMeta = () => call<Meta>("/meta")

export const resumeRun = (id: string, answer: object | null) =>
  call<{ thread_id: string }>(`/runs/${id}/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  })
