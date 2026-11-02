import { createElement } from "react"
import { renderToString } from "react-dom/server"
import { afterEach, expect, test, vi } from "vitest"
import { ApiError, correctResume, uploadResume } from "../api/client"
import type { ResumeFacts } from "../api/types"
import { ChipList } from "../customers/ChipList"
import { changes, draftOf } from "../customers/resumeForm"

const reply = (status: number, body: object) => new Response(JSON.stringify(body), { status })
const facts: ResumeFacts = {
  roles: [{ title: "Data Engineer", start: "2019", end: "Present" }],
  skills: [{ name: "Python", added: false }, { name: "dbt", added: true }],
  seniority: "mid",
  locations: ["Austin"],
  years: 7,
}

afterEach(() => vi.unstubAllGlobals())

test("an upload sends the raw body, not JSON", async () => {
  const fetch = vi.fn().mockImplementation(async () => reply(200, { facts, uploaded_at: "2026-11-01T00:00:00Z", replaced: false }))
  vi.stubGlobal("fetch", fetch)
  await uploadResume("c1", "pasted text")
  expect(fetch.mock.calls[0][0]).toMatch(/\/customers\/c1\/resume$/)
  expect(fetch.mock.calls[0][1]).toMatchObject({ method: "PUT", body: "pasted text" })
  expect(fetch.mock.calls[0][1].headers).toBeUndefined()
})

test("a refusal keeps the server's message", async () => {
  const message = "This file is over 2 MB. Upload a smaller one or paste the text"
  vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => reply(413, { code: "too_big", message })))
  await expect(uploadResume("c1", "x")).rejects.toMatchObject({ status: 413, code: "too_big", message })
  await expect(uploadResume("c1", "x")).rejects.toBeInstanceOf(ApiError)
})

test("a correction sends only the fields that changed", async () => {
  const draft = { ...draftOf(facts), skills: ["Python", "dbt", "Airflow"] }
  expect(changes(facts, draft)).toEqual({ skills: ["Python", "dbt", "Airflow"] })
  expect(changes(facts, draftOf(facts))).toEqual({})
  const fetch = vi.fn().mockImplementation(async () => reply(200, { facts, uploaded_at: "2026-11-01T00:00:00Z", replaced: false }))
  vi.stubGlobal("fetch", fetch)
  await correctResume("c1", changes(facts, draft))
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ skills: ["Python", "dbt", "Airflow"] })
})

test("only a skill the server marked added carries the tag", () => {
  const html = renderToString(
    createElement(ChipList, { label: "skill", items: ["Python", "dbt"], max: 30, maxChars: 40, added: new Set(["dbt"]), onChange: () => {} }),
  )
  expect(html.match(/added by CSM/g)).toHaveLength(1)
  expect(html.indexOf("dbt")).toBeLessThan(html.indexOf("added by CSM"))
})
