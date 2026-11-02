import { expect, test } from "vitest"
import { TABS, downloadUrl } from "../brief/documents"

test("a finished Run has the Market Brief and the Customer Recommendation, each with its own downloads", () => {
  expect(TABS.map((t) => t.label)).toEqual(["Market Brief", "Customer Recommendation"])
  expect(downloadUrl("t1", "brief", "md")).toMatch(/\/runs\/t1\/brief\.md$/)
  expect(downloadUrl("t1", "recommendation", "json")).toMatch(/\/runs\/t1\/recommendation\.json$/)
})
