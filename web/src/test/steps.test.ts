import { expect, test } from "vitest"
import { STEPS, backEdges } from "../run/steps"
import graph from "./meta-graph.json"

test("every node in /meta has a Step label", () => {
  const labelled = new Set(STEPS.flatMap((s) => s.nodes))
  expect(graph.nodes.filter((n) => !labelled.has(n.id))).toEqual([])
})

test("the Steps have exactly the five back-edges", () => {
  expect(backEdges(graph).sort()).toEqual(["approve→plan", "ask→read", "check→write", "few→widen", "widen→search"])
})
