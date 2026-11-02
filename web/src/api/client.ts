import type { Customer, Dimension, Me, Meta, Profile, ProfileField, ResumeInfo, ResumePatch, RunDetail, RunRecord } from "./types"

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

export const SIGNED_OUT = "signed-out"

type Init = Omit<RequestInit, "headers"> & { headers?: Record<string, string> }

async function call<T>(path: string, init?: Init): Promise<T> {
  // The session is a cookie, so the browser sends it; nothing is added here.
  const response = await fetch(`${API}${path}`, { ...init, credentials: "same-origin" })
  if (response.ok) return response.status === 204 ? (undefined as T) : response.json()
  // Refusals carry {code, message}; anything else (a proxy error, say) still becomes an ApiError.
  const body = await response.json().catch(() => ({}))
  if (body.code === "signed_out") dispatchEvent(new Event(SIGNED_OUT))
  throw new ApiError(response.status, body.code ?? "unknown", body.message ?? response.statusText, body.errors)
}

const json = (method: string, body: object): Init => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })

export const startRun = (customer_id: string, request_text: string, focus: Dimension[], use_profile: boolean) =>
  call<{ thread_id: string }>("/runs", json("POST", { customer_id, request_text, focus, use_profile }))

export const deleteRun = (id: string) => call<void>(`/runs/${id}`, { method: "DELETE" })

export const getMe = () => call<Me>("/me")

export const logOut = () => call<void>("/auth/logout", { method: "POST" })

export const listCustomers = () => call<Customer[]>("/customers")

export const addCustomer = (name: string, note: string) => call<Customer>("/customers", json("POST", { name, note }))

export const editCustomer = (id: string, fields: { name?: string; note?: string }) =>
  call<Customer>(`/customers/${id}`, json("PATCH", fields))

export const deleteCustomer = (id: string) => call<void>(`/customers/${id}`, { method: "DELETE" })

export const getResume = (id: string) => call<ResumeInfo>(`/customers/${id}/resume`)

// The server sniffs the bytes, so a file and pasted text go up the same way, raw.
export const uploadResume = (id: string, body: Blob | string) => call<ResumeInfo>(`/customers/${id}/resume`, { method: "PUT", body })

export const correctResume = (id: string, patch: ResumePatch) => call<ResumeInfo>(`/customers/${id}/resume`, json("PATCH", patch))

export const deleteResume = (id: string) => call<void>(`/customers/${id}/resume`, { method: "DELETE" })

export const getProfile = (id: string) => call<Profile>(`/customers/${id}/profile`)

export const editProfile = (id: string, change: { set?: Partial<Record<ProfileField, string | string[]>>; remove?: ProfileField[] }) =>
  call<Profile>(`/customers/${id}/profile`, json("PATCH", change))

export const clearProfile = (id: string) => call<void>(`/customers/${id}/profile`, { method: "DELETE" })

export const listRuns = () => call<RunRecord[]>("/runs")

export const getRun = (id: string) => call<RunDetail>(`/runs/${id}`)

export const getMeta = () => call<Meta>("/meta")

export const resumeRun = (id: string, answer: object | null) =>
  call<{ thread_id: string }>(`/runs/${id}/resume`, json("POST", { answer }))

export const cancelRun = (id: string) => call<{ node: string | null; reason: string }>(`/runs/${id}/cancel`, { method: "POST" })
