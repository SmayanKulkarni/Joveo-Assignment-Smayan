import { expect, test } from "vitest"
import type { Pause } from "../api/types"
import { empty, reduce } from "../run/reducer"

const pause: Pause = { kind: "clarify", payload: { questions: [] } }

test("answering collapses the Pause into a record on its own turn", () => {
  let state = reduce(empty, { type: "node_started", node: "clarify" })
  state = reduce(state, { type: "paused", pause })
  state = reduce(state, { type: "answered", record: "You answered 1 question" })
  expect(state.pause).toBeNull()
  expect(state.turns).toMatchObject([{ step: "ask", results: [], answer: "You answered 1 question" }])
  // The rerun node's NodeStarted stays in the same turn instead of opening another.
  expect(reduce(state, { type: "node_started", node: "clarify" }).turns).toHaveLength(1)
})

test("a reopened Pause with no history still gets a turn for its record", () => {
  const state = reduce(reduce(empty, { type: "paused", pause }), { type: "answered", record: "You skipped the questions" })
  expect(state.turns.map((t) => t.step)).toEqual(["ask"])
})
