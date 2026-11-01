import { expect, test } from "vitest"
import type { Pause, WireEvent } from "../api/types"
import { empty, reduce } from "../run/reducer"
import type { RunState } from "../run/reducer"
import demo from "./demo-run.json"

const events = demo.events as WireEvent[]

// The client clears a Pause when the user answers, which the feed itself doesn't carry.
function play(feed: WireEvent[], from: RunState = empty): RunState {
  return feed.reduce((state, event) => reduce(state.pause ? reduce(state, { type: "answered", record: "answered" }) : state, event), from)
}

test("the Demo Run feed reaches its end state", () => {
  const state = play(events)
  expect(state.turns.map((t) => t.step)).toEqual([
    "read", "ask", "read", "plan", "approve", "search", "filter", "few", "widen", "search", "filter",
    "postings", "normalise", "stats", "write", "check", "write", "check", "finish",
  ])
  expect(state.ending).toEqual({ kind: "done" })
  expect(state.pause).toBeNull()
  const tools = state.turns.flatMap((t) => t.tools)
  expect(tools.length).toBeGreaterThan(0)
  expect(tools.every((t) => t.result !== null && t.pill)).toBe(true)
  expect(state.turns.find((t) => t.step === "postings")?.progress).toEqual({ done: 6, total: 6 })
})

test("one batch equals the events one by one", () => {
  const head = events.slice(0, 40)
  expect(reduce(empty, { type: "batch", events: head })).toEqual(head.reduce(reduce, empty))
})

test("tool results pair first-in-first-out by name", () => {
  const call = (summary: string) => ({ type: "tool_called", name: "search_adzuna", summary }) as const
  let state = reduce(empty, { type: "node_started", node: "tools" })
  state = [call("a"), call("b")].reduce(reduce, state)
  state = reduce(state, { type: "tool_returned", name: "search_adzuna", summary: "first" })
  expect(state.turns[0].tools.map((t) => t.result)).toEqual(["first", null])
  // ApiCalled lands on the first card of that source without a pill.
  state = reduce(state, { type: "api_called", source: "adzuna", cached: true, count: 0, failed: false })
  state = reduce(state, { type: "api_called", source: "adzuna", cached: false, count: 7, failed: false })
  expect(state.turns[0].tools.map((t) => t.pill)).toEqual(["cached", "7"])
  // Stopped marks what is still open.
  expect(reduce(state, { type: "stopped", node: "tools", reason: "x" }).turns[0].tools.map((t) => t.interrupted)).toEqual([undefined, true])
})

test("no reasoning means no thinking text, and JSON tokens never show", () => {
  let state = reduce(empty, { type: "node_started", node: "plan" })
  expect(state.turns[0].drafting).toBe("Drafting the search plan…")
  state = reduce(state, { type: "token", node: "plan", text: '{"titles"' })
  expect(state.turns[0].drafting).toBeNull()
  expect(state.texts).toEqual({})
  state = reduce(state, { type: "reasoning", node: "plan", text: "hmm" })
  expect(state.texts[0]).toEqual({ thinking: "hmm", prose: "" })
})

test("a reset to the base keeps live text", () => {
  let state = reduce(empty, { type: "node_started", node: "fetch_agent" })
  state = reduce(state, { type: "token", node: "fetch_agent", text: "Searching" })
  const reset = reduce(state, { type: "reset", to: empty, keepTexts: true })
  expect(reset.turns).toEqual([])
  expect(reset.texts[0].prose).toBe("Searching")
  expect(reset.animate).toBe(false)
  expect(reduce(state, { type: "reset", to: empty }).texts).toEqual({})
})

test("the gap line only follows a replay that reached a streaming turn", () => {
  const started = reduce(empty, { type: "node_started", node: "fetch_agent" })
  expect(reduce(started, { type: "caught_up" }).gap).toBe(true)
  expect(reduce(reduce(empty, { type: "node_started", node: "intake" }), { type: "caught_up" }).gap).toBe(false)
  const paused: Pause = { kind: "clarify", payload: { questions: [] } }
  expect(reduce(reduce(started, { type: "paused", pause: paused }), { type: "caught_up" }).gap).toBe(false)
})
