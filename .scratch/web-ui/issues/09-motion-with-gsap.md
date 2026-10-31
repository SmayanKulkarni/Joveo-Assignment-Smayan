# Motion with GSAP

Type: grilling
Status: open
Assignee: none
Blocked by: [Trace graph](05-trace-graph.md), [Live Run view](06-live-run-view.md)

## Question

Which animations does the UI have, and how does GSAP drive each one without making a streaming page jittery?

- The inventory: node activation and completion, edge flow along the active path, the overall progress bar, extraction progress, tool-card enter and resolve, token reveal, sidebar row enter and status change, Pause card attention, and the Brief arriving.
- Timing and easing tokens shared by all of them, and a motion budget (what may run at once while tokens stream at speed).
- Mapping state to animation: state change drives a tween, never the other way round, so a burst of events or a reconnect replay settles on the final state rather than playing back every step.
- `useGSAP` scoping and cleanup per component, from [Research: graph rendering and GSAP in React](02-research-graph-rendering-and-gsap.md).
- `prefers-reduced-motion`: what is removed, and what remains as a plain state change.
- Performance: avoiding layout thrash on the token stream, and pausing off-screen tweens.

Resolution is the animation table (trigger, target, tween, duration) and the shared tokens.
