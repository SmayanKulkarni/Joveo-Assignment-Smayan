import { expect, test } from "vitest"
import type { Pause, RunDetail, WireEvent } from "../api/types"
import { fromLog } from "../run/fromLog"
import { empty, reduce } from "../run/reducer"
import type { RunState } from "../run/reducer"
import { STEPS } from "../run/steps"
import { traceReduce } from "../run/trace"
import demo from "./demo-run.json"

const events = demo.events as WireEvent[]
const started = (node: string): WireEvent => ({ type: "node_started", node })

// The client clears a Pause when the user answers, which the feed itself doesn't carry.
const play = (feed: WireEvent[], from: RunState = empty) =>
  feed.reduce((state, event) => reduce(state.pause ? reduce(state, { type: "answered", record: "answered" }) : state, event), from)

const shape = (state: RunState) =>
  Object.fromEntries(STEPS.map((s) => [s.id, [state.trace.steps[s.id].status, state.trace.steps[s.id].visits]]))

test("progress never decreases, and Done snaps it to the end", () => {
  let last = 0
  let state = empty
  for (const event of events) {
    state = play([event], state)
    expect(state.trace.progress).toBeGreaterThanOrEqual(last)
    last = state.trace.progress
  }
  expect(last).toBe(1)
  // The Demo Run loops, which sends Steps back to idle; the bar still held.
  expect(state.trace.looped).toContain("widen→search")
})

test("a loop resets the Steps between, except optional ones that ran", () => {
  const feed: WireEvent[] = ["fetch_agent", "relevance", "broaden", "fetch_agent"].map(started)
  const { trace } = play(feed)
  expect(trace.steps.filter.status).toBe("idle") // ran, then reset
  expect(trace.steps.widen.status).toBe("done") // optional and ran, so kept
  expect(trace.steps.search).toMatchObject({ status: "active", visits: 2 })
  expect(trace.looped).toEqual(["widen→search"])
  expect(trace.steps.ask.status).toBe("skipped")
})

test("only a Pause's own Step waits, and the Step before it is done", () => {
  const pause: Pause = { kind: "plan_review", payload: { plan: {} as never, assumptions: [] } }
  const { trace } = play([started("plan"), started("plan_review"), { type: "paused", pause }])
  expect(trace.steps.approve.status).toBe("waiting")
  expect(trace.steps.plan.status).toBe("done")
  expect(trace.steps.search.status).toBe("idle")
})

test("a Stopped Step goes red and Resume makes it run again without a new visit", () => {
  let state = play([started("fetch_agent"), started("normalise_skills"), { type: "stopped", node: "normalise_skills", reason: "boom" }])
  expect(state.trace).toMatchObject({ finished: "failed", steps: { normalise: { status: "failed", visits: 1 } } })
  state = reduce(reduce(state, { type: "resumed" }), started("normalise_skills"))
  expect(state.ending).toBeNull()
  expect(state.trace).toMatchObject({ finished: null, steps: { normalise: { status: "active", visits: 1 } } })
})

test("a replay gives the state the live feed gave", () => {
  const live = play(events)
  const replayed = play(events, reduce(live, { type: "reset" }))
  expect(replayed.trace).toEqual(live.trace)
})

test("a reload lands where the live trace was at each Pause", () => {
  const pauses = events.flatMap((e, i) => (e.type === "paused" ? [i] : []))
  expect(pauses.length).toBeGreaterThan(1)
  for (const at of pauses) {
    const feed = events.slice(0, at + 1)
    const run_log = feed.flatMap((e) => (e.type === "node_done" ? e.notes.map((message) => ({ node: e.node, kind: "note", message })) : []))
    const pause = (feed.at(-1) as Extract<WireEvent, { type: "paused" }>).pause
    const detail = {
      record: { thread_id: "t", summary: "s", status: "paused", error: null, created_at: "", updated_at: "" },
      request_text: "r", focus: [], pause, stopped_at: null, run_log, live_from: null, brief: null, sample: [],
    } as RunDetail
    expect(shape(fromLog(detail))).toEqual(shape(play(feed)))
  }
})

test("a Step passed without an event is done, so a reload at a later Step shows no hole", () => {
  const { trace } = play([started("plan"), started("normalise_skills")])
  expect(trace.steps.postings).toMatchObject({ status: "done", visits: 1 })
  expect(trace.steps.search.status).toBe("done")
  expect(trace.steps.few.status).toBe("skipped")
})

test("traceReduce returns the same object for events it ignores", () => {
  expect(traceReduce(empty.trace, { type: "caught_up" })).toBe(empty.trace)
})
