import { expect, test } from "vitest"
import { empty, reduce } from "../run/reducer"
import { STEPS, backEdges, sourceName } from "../run/steps"
import graph from "./meta-graph.json"

test("every node in /meta has a Step label", () => {
  const labelled = new Set(STEPS.flatMap((s) => s.nodes))
  expect(graph.nodes.filter((n) => !labelled.has(n.id))).toEqual([])
})

test("the Steps have exactly the five back-edges", () => {
  expect(backEdges(graph).sort()).toEqual(["approve→plan", "ask→read", "check→write", "few→widen", "widen→search"])
})

test("a search_arbeitnow call lights the search Step and is named Arbeitnow", () => {
  const { trace } = reduce(reduce(empty, { type: "node_started", node: "tools" }), { type: "tool_called", name: "search_arbeitnow", summary: "x" })
  expect(trace.steps.search.status).toBe("active")
  expect(sourceName(trace.tool!.name)).toBe("Arbeitnow")
})
