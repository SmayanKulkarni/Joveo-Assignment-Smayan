import { afterEach, expect, test, vi } from "vitest"
import { ApiError, SIGNED_OUT, getMe, listRuns, logOut, startRun } from "../api/client"

const reply = (status: number, body: object) => new Response(JSON.stringify(body), { status })

afterEach(() => vi.unstubAllGlobals())

test("a signed_out refusal tells the app, once per call, and still throws", async () => {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => reply(401, { code: "signed_out", message: "Sign in to continue" })))
  const heard = vi.fn()
  vi.stubGlobal("dispatchEvent", heard)
  await expect(getMe()).rejects.toMatchObject({ status: 401, code: "signed_out" })
  expect(heard).toHaveBeenCalledOnce()
  expect((heard.mock.calls[0][0] as Event).type).toBe(SIGNED_OUT)
})

test("other refusals become an ApiError and don't sign anyone out", async () => {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => reply(404, { code: "not_found", message: "No such Customer" })))
  const heard = vi.fn()
  vi.stubGlobal("dispatchEvent", heard)
  await expect(startRun("c", "x", [])).rejects.toBeInstanceOf(ApiError)
  expect(heard).not.toHaveBeenCalled()
})

test("a run starts inside a customer, and a 204 has no body to read", async () => {
  const fetch = vi.fn().mockImplementation(async () => new Response(null, { status: 204 }))
  vi.stubGlobal("fetch", fetch)
  await expect(logOut()).resolves.toBeUndefined()
  fetch.mockImplementation(async () => reply(201, { thread_id: "t" }))
  await startRun("cust", "x", ["skills"])
  expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({ customer_id: "cust", request_text: "x", focus: ["skills"] })
  fetch.mockImplementation(async () => reply(200, []))
  await listRuns()
})
