# 11: Motion

**What to build:** the UI comes alive with GSAP: the trace animates, tool cards resolve, the sidebar's running rows pulse, and the Brief arrives, all without making a streaming page jittery. React still renders every final state, so the animations are never what the UI relies on. Spec: [Web UI LLD](../../../docs/lld/web-ui.md) §10.

**Blocked by:** 05: Read the Market Brief; 06: Find earlier Runs in the sidebar; 10: Trace panel and progress bar

**Status:** ready-for-agent

If time runs short, this ticket can be dropped, or cut down one-shots first, and the UI stays correct.

- [ ] One `useMotion` helper wraps `useGSAP` and `matchMedia`, and each animated component owns one call scoped to itself
- [ ] Every row in §10's table is implemented with the shared duration and easing tokens
- [ ] GSAP only plays into a state React already rendered: disabling `useMotion` changes no state or layout
- [ ] There is no per-token tween, and the caret is the only motion on prose
- [ ] Only `transform`, `opacity` and SVG attributes tween, so progress bars use `scaleX`, not `width`
- [ ] Repeating tweens end when their state changes, and none outlives its component under `<StrictMode>`
- [ ] A reload, replay or reopened Run plays no one-shot, since `animate` is false until `caught_up`
- [ ] At most one loop dot plays per batch
- [ ] Scrolling to the live Step is native, and instant under reduced motion
- [ ] Checked by hand under OS reduced motion: no repeating tween runs, and every state still reads
- [ ] Checked by hand: a fast token stream stays smooth with the trace animating, and the console stays clean
