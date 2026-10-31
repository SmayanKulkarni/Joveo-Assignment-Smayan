# Research: graph rendering and GSAP in React

Type: research
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

What is the cheapest way to draw an animated trace graph of about 15 nodes with loops, and what does GSAP need to work cleanly in React?

- Hand-written SVG animated by GSAP against React Flow (or a similar library) with a fixed layout: bundle size, how well each lets GSAP drive node and edge state, and what a loop edge (`broaden` back to `fetch_agent`, `clarify` back to `intake`) costs in each.
- A layout approach for a graph that is mostly a pipeline with a few back-edges: a fixed column grid, or a layout library such as `dagre` or `elkjs`.
- GSAP's current licence and package terms (whether plugins such as `MotionPathPlugin` and `DrawSVGPlugin` are free to use), and the current `gsap` and `@gsap/react` versions.
- `useGSAP`: cleanup and scoping so animations do not leak when React remounts, and how it behaves under React 19 strict mode.
- `prefers-reduced-motion` handling with `gsap.matchMedia`.

Read the official docs for each; capture findings in the ticket.

## Answer

**Recommendation.** Hand-written SVG in React, a fixed layout computed from a stage-column grid, GSAP driving it. No React Flow, no dagre/elkjs.
- Topology comes from the backend as `{nodes: [{id, owner}], edges: [{source, target, conditional}]}` (from `OWNERS`, `EDGES`, `CONDITIONAL`). The owner picks the column (`request_plan`, `collection`, `analysis`, `brief`); the row is the node's index within its owner. START and END sit in the first and last column. A back-edge is any edge whose target has a lower column, or the same column and a lower row: draw it as a cubic Bezier bowed out to the left of the column.
- Versions to pin: `gsap` 3.15.0, `@gsap/react` 2.1.2 (peers `gsap ^3.12.5`, `react >=17`), React 19.3.1, Vite 8.3.5. Import plugins from `gsap/DrawSVGPlugin` and `gsap/MotionPathPlugin`, then `gsap.registerPlugin(useGSAP, DrawSVGPlugin, MotionPathPlugin)`. All free.
- Setup: one `useGSAP(() => { gsap.matchMedia().add({ full, reduced }, ctx => ...) }, { scope: svgRef })`. Active node pulse = `scale` yoyo on the node's inner `<rect>`; edge flow = `strokeDashoffset` on a dashed path (or a `MotionPathPlugin` dot along it); completion check = `DrawSVGPlugin` `drawSVG: 0 -> 100%` on a check path. Re-run when event-derived node status changes (`dependencies`, with `revertOnUpdate: true`), and wrap anything created later in `contextSafe`.

### Findings (V = verified in the throwaway app, D = read in the docs)
- **Licence (D).** GSAP is under the Standard "no charge" licence, commercial use included; formerly paid plugins such as SplitText and MorphSVG "can be used in commercial projects at no charge". The restriction is visual no-code animation tools that compete with Webflow, which does not apply. https://gsap.com/standard-license
- **Plugins from npm (D, V).** "All the plugins are now freely available on npm", imported per plugin from `gsap/<Name>`. `DrawSVGPlugin.js`, `MotionPathPlugin.js` and `MorphSVGPlugin.js` are in `node_modules/gsap`; the first two built and ran in my test. https://gsap.com/docs/v3/Installation/
- **Versions (V).** `npm view`: gsap 3.15.0 (licence field "Standard 'no charge' license"), @gsap/react 2.1.2, react 19.3.1, @xyflow/react 12.12.0, @dagrejs/dagre 3.1.3, elkjs 0.12.1. `@gsap/react` peer is `react >=17`; my test ran it on React 19.3.1 with no console errors.
- **`useGSAP` cleanup (D, V).** Drop-in for `useEffect`/`useLayoutEffect` built on `gsap.context()`; everything created while the callback runs is reverted on unmount. `scope` (a ref) limits selector strings to descendants. `revertOnUpdate` defaults to `false`, so a dependency change does not revert until unmount. Tweens created later (handlers, async) need `contextSafe`, or they are neither scoped nor cleaned up. https://gsap.com/resources/React/
- **Strict mode (D, V).** Dev double-invokes effects; the hook reverts in between so `from` tweens and duplicates do not pile up. Measured under `<StrictMode>` in `vite dev`: 3 looping tweens after mount (not 6), 0 after unmounting the component, 4 after remount (the 3 loops plus the one-shot `drawSVG` from-tween, still running). No leaks.
- **Animating SVG in React (V).** On hand-written `<path>`s inside `useGSAP` with `scope`: `strokeDashoffset` moved from -11.8px to -19.5px in 300 ms; a `MotionPathPlugin` dot got a live `matrix(...)` transform along the path; `drawSVG` set `stroke-dasharray` on the paths; a `<rect>` scale yoyo applied.
- **`gsap.matchMedia` and reduced motion (D, V).** `mm.add({ full: '(prefers-reduced-motion: no-preference)', reduced: '(prefers-reduced-motion: reduce)' }, ctx => ...)`; `ctx.conditions` says which matched. It uses `gsap.context()` internally; setup reverts when the query stops matching, and a returned function is for non-GSAP cleanup only. https://gsap.com/docs/v3/GSAP/gsap.matchMedia()/ Verified by stubbing `window.matchMedia` to report `reduce` and remounting: 0 running tweens, edges set to the static colour, `strokeDashoffset` stayed 0. The `useGSAP` page does not mention `matchMedia`; it worked inside `useGSAP` with `scope` here.
- **React Flow cost (V, D).** 12.12.0, 1.2 MB unpacked, +85 kB gzip over the hand-SVG build (table). Default routing with top/bottom handles gave long overlapping swoops for back-edges and same-column edges in my 19-node/30-edge test, so loops need a custom edge path plus left/right handles: the same hand computation as plain SVG, inside a framework. Its own animation docs use SVG `<animateMotion>` or the Web Animations API on custom edges, not GSAP. https://reactflow.dev/examples/edges/animating-edges
- **GSAP and React Flow node wrappers (V).** `.react-flow__node` carries RF's inline `translate3d(...)`; GSAP parsed it and rewrote it as `translate3d(...) scale(...)`, so tweening the wrapper can fight RF's positioning on later moves. Animate an inner element in a custom node instead. Edge `<path>` dashoffset tweens worked.
- **Layout libraries (D, V).** React Flow's layout page: dagre is simple and fast, with no edge routing; elkjs is the most configurable, async, and "by far the largest". https://reactflow.dev/learn/layouting/layouting dagre has `acyclicer: 'greedy'` (default off) to break cycles by reversing or dropping a feedback arc set, so which edge it treats as the "back" edge is the heuristic's choice, not ours. https://github.com/dagrejs/dagre/wiki Our stage order is known, so a column grid gives a deterministic layout for free.
- **Loop-edge cost by option.** Hand SVG: one extra branch in the path function (about 6 lines). React Flow: custom edge component, handle placement and path maths. dagre: node coordinates only (no edge routing per the RF page), so back-edges are still drawn by hand. elkjs: routes edges but is async and +453 kB gzip.

### Measured production-build sizes (Vite 8.3.5, minified, gzip)
| Build | gzip |
|---|---|
| React 19 + react-dom only (baseline) | 68.6 kB |
| + `@gsap/react` + GSAP core + `matchMedia`, hand-written SVG (a) | 97.0 kB (+28.4) |
| (a) + `DrawSVGPlugin` + `MotionPathPlugin` | 107.2 kB (+10.3) |
| React + `@xyflow/react` + GSAP core, no plugins (b) | 156.4 kB (153.9 JS + 2.6 CSS) |
| baseline + `@dagrejs/dagre` | 84.3 kB (+15.7) |
| baseline + `elkjs` bundled | 522.1 kB (+453.5) |

Test apps (19 nodes, 30 edges from the real `EDGES`/`CONDITIONAL`) are in `C:\Users\SMAYAN~1\AppData\Local\Temp\claude\d--Joveo\82a0791c-35de-4261-b0fd-f9b6c47d5b48\scratchpad\graph-research\{a,b,c}`. Hand SVG saves about 49 kB gzip against React Flow; the larger win is control over loops and no wrapper-transform clash.

### Not verified
- Visual quality of the hand-SVG layout: drawn for size and animation tests only; spacing, label widths and back-edge clearance for the real 17 nodes are untuned, and loop overlap is unchecked.
- The real OS `prefers-reduced-motion` setting: I stubbed `window.matchMedia`, not the OS or browser flag.
- StrictMode in a production build: dev double-invocation was tested; the production build was only measured.
- `MorphSVGPlugin`: present in the package, not built or run (not needed for this graph).
- Licence detail: the licence page does not name DrawSVG or MotionPath; the "all plugins free on npm" claim is from the Installation page and the files ship in the npm package.
- Fan-out display for `batch_extract`, mid-session topology changes, narrow viewports, and whether pan/zoom is wanted: design questions, not tested.
