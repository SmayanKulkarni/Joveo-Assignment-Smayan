import { afterEach, expect, test, vi } from "vitest"
import { ApiError, listRuns, startRun } from "../api/client"

const reply = (status: number, body: object) => new Response(JSON.stringify(body), { status })
const denied = () => reply(401, { code: "access_denied", message: "This needs the access code" })
const codeOf = (call: unknown[]) => (call[1] as { headers?: Record<string, string> }).headers?.["X-Access-Code"]

function stub(fetch: ReturnType<typeof vi.fn>, answer: string | null) {
  const prompt = vi.fn(() => answer)
  const stored = new Map<string, string>()
  vi.stubGlobal("fetch", fetch)
  vi.stubGlobal("window", { prompt })
  vi.stubGlobal("localStorage", { getItem: (k: string) => stored.get(k) ?? null, setItem: (k: string, v: string) => stored.set(k, v) })
  return prompt
}

afterEach(() => vi.unstubAllGlobals())

test("a refused write asks for the code, retries once, and remembers it", async () => {
  const fetch = vi.fn().mockResolvedValueOnce(denied()).mockImplementation(async () => reply(201, { thread_id: "t" }))
  const prompt = stub(fetch, "sesame")

  await expect(startRun("x", [])).resolves.toEqual({ thread_id: "t" })
  expect(prompt).toHaveBeenCalledOnce()
  expect(fetch.mock.calls.map(codeOf)).toEqual([undefined, "sesame"])

  await startRun("y", [])
  expect(prompt).toHaveBeenCalledOnce()
  expect(codeOf(fetch.mock.calls[2])).toBe("sesame")
})

test("a wrong code stops after one retry, and cancelling sends nothing more", async () => {
  const wrong = vi.fn().mockImplementation(async () => denied())
  stub(wrong, "nope")
  await expect(startRun("x", [])).rejects.toBeInstanceOf(ApiError)
  expect(wrong).toHaveBeenCalledTimes(2)

  const cancelled = vi.fn().mockImplementation(async () => denied())
  stub(cancelled, null)
  await expect(startRun("x", [])).rejects.toMatchObject({ code: "access_denied" })
  expect(cancelled).toHaveBeenCalledOnce()
})

test("reads never send the code", async () => {
  const fetch = vi.fn().mockImplementation(async () => reply(200, []))
  stub(fetch, null)
  localStorage.setItem("talent-scout-access-code", "sesame")
  await listRuns()
  expect(codeOf(fetch.mock.calls[0])).toBeUndefined()
})
