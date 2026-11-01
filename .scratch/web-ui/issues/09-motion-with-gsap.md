# Motion with GSAP

Type: grilling
Status: resolved
Assignee: smayankulkarni05
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

## Answer

Decided by the agent (the user delegated every decision on 2026-10-31). The timings are the ones reviewed in the [trace prototype](../prototype/trace/index.html), collected into tokens.

**The one rule: React renders the final state, and GSAP only plays the way into it.** Classes and attributes carry every state, so tweens are `from` or decorative. It follows that:
- Reduced motion is simply no tweens, with nothing else to write and no state lost.
- A burst or replay can't play back steps, since a frame's batch renders once.
- With `animate: false` (before `caught_up`, and on any reopened Run) no one-shot fires.

**One helper, `useMotion(fn, deps, scope)` in `motion.ts`,** wraps `useGSAP` with `revertOnUpdate: true`, and runs `fn` inside `gsap.matchMedia().add("(prefers-reduced-motion: no-preference)", ...)`. Each animated component owns one call scoped to its own element, with `deps` being its state, so a loop ends itself when the state changes. Plugins register once in `motion.ts`. Handlers use `contextSafe`. Previous state comes from a ref, to tell an entry from a re-render.

**Tokens.**
```ts
DUR  = { fast: 0.15, base: 0.25, slow: 0.5 }
EASE = { out: "power2.out", pop: "back.out(3)", linear: "none", settle: "elastic.out(1.2,0.3)" }
```

| Trigger | Target | Tween | Duration, ease |
|---|---|---|---|
| Step becomes active | Step icon arc | rotate 360, repeating | 0.9 s, linear |
| | Step ring | opacity .55 to 0, scale 1 to 1.04, repeating | 1.3 s, out |
| Rail segment is live | Segment `stroke-dashoffset` | 10 to 0, repeating | 0.6 s, linear |
| Step becomes done | Check path | `drawSVG` 0 to 100% | 0.35 s, out |
| Step starts waiting | Step ring | opacity .6 to 0, scale 1 to 1.05, repeating | 2 s, sine.out |
| Step fails | Step group | x -3 to 0 | slow, settle |
| Counter changes | Badge | scale 1.6 to 1 | 0.4 s, pop |
| Loop taken (`fx`) | Dot on the back-edge | `motionPath` 0 to 1, then hidden | 0.9 s, power1.inOut |
| Progress changes | Overall bar | `scaleX`, origin left | slow, out |
| `ExtractProgress` | Turn's bar and the Step's bar | `scaleX` | base, out |
| New turn | Turn | y 6 to 0, opacity 0 to 1 | base, out |
| Tool card enters | Card | y 4 to 0, opacity 0 to 1 | fast, out |
| Tool card resolves | Spinner out, check `drawSVG` | as Step done | 0.35 s, out |
| Prose is streaming | Caret | opacity 1 to 0, repeating | slow, stepped |
| Sidebar row is `running` | Badge dot | opacity 1 to .25, scale to .7, repeating | 0.6 s, sine.inOut |
| New sidebar row | Row | opacity 0 to 1 | base, out |
| Row status changes | Badge | opacity 0 to 1 | base, out |
| Pause card arrives | Card | y 8 to 0, opacity, then border pulse twice | base, out |
| Brief arrives live | Sections | y 8 to 0, opacity, stagger .06 | base, out |

**Token reveal has no per-token tween.** Text is appended per frame. A tween per fragment is exactly the jitter this ticket warns of, and the caret is the only motion on prose.

**Budget.** Only `transform`, `opacity` and SVG attributes tween, never layout, so the prototype's bar `width` becomes `scaleX`, and `<details>` opens instantly with no height tweens. At any moment the repeating tweens are: the active Step's three (arc, ring, rail), one caret, and one dot per `running` sidebar row. One-shots on stream content fire per turn or per card, never per token. At most one loop dot plays per batch.

**Scrolling** uses native `scrollIntoView({behavior: "smooth", block: "nearest"})` for the live Step, with `"auto"` under reduced motion, so `ScrollToPlugin` isn't needed.

**Off-screen.** Below 900 px the trace panel is not mounted, so its loops don't exist, and the strip has only its bar. GSAP's ticker follows `requestAnimationFrame`, so a hidden tab costs nothing and `lagSmoothing`'s default avoids a jump on return. No `IntersectionObserver` per tween: the live Step is kept in view anyway.

**Reduced motion leaves:** the static icons (arc, pause bars, check, cross), final colours, instantly set bars, the counter, and instant scrolling. No repeating tween runs, which the prototype checked (3 live loops became 0).

Bundle: `gsap` with `DrawSVGPlugin` and `MotionPathPlugin` on React 19 built to 106.7 kB gzip with the pinned toolchain, in line with the research estimate.
