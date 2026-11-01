import type { Dimension, Meta, RunDetail, RunRecord } from "./types"

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

// Empty locally, where the app and API share an origin; set at build time on a separate frontend host.
export const API = `${(import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "")}/api`

const CODE_KEY = "talent-scout-access-code"

// Storage can throw or be missing (a private window), and then the code just lasts for this one request.
function storedCode(): string | null {
  try {
    return localStorage.getItem(CODE_KEY)
  } catch {
    return null
  }
}

function storeCode(code: string) {
  try {
    localStorage.setItem(CODE_KEY, code)
  } catch {}
}

type Init = Omit<RequestInit, "headers"> & { headers?: Record<string, string> }

async function call<T>(path: string, init?: Init, code = storedCode(), retried = false): Promise<T> {
  const headers = init?.method && code ? { ...init.headers, "X-Access-Code": code } : init?.headers
  const response = await fetch(`${API}${path}`, { ...init, headers })
  if (response.ok) return response.json()
  // Refusals carry {code, message}; anything else (a proxy error, say) still becomes an ApiError.
  const body = await response.json().catch(() => ({}))
  if (body.code === "access_denied" && !retried) {
    const answer = window.prompt("Enter the access code to continue")
    if (answer) {
      storeCode(answer)
      return call(path, init, answer, true)
    }
  }
  throw new ApiError(response.status, body.code ?? "unknown", body.message ?? response.statusText, body.errors)
}

export const startRun = (request_text: string, focus: Dimension[]) =>
  call<{ thread_id: string }>("/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request_text, focus }),
  })

export const listRuns = () => call<RunRecord[]>("/runs")

export const getRun = (id: string) => call<RunDetail>(`/runs/${id}`)

export const getMeta = () => call<Meta>("/meta")

export const resumeRun = (id: string, answer: object | null) =>
  call<{ thread_id: string }>(`/runs/${id}/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  })

export const cancelRun = (id: string) => call<{ node: string | null; reason: string }>(`/runs/${id}/cancel`, { method: "POST" })
