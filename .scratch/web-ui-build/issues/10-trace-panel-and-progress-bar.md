# 10: Trace panel and progress bar

**What to build:** beside the stream, a trace panel shows which of the 14 Steps the Run is on, what remains, where it looped, and how far along it is, live and after a reload. No animation yet: every state reads correctly on its own. Spec: [Web UI LLD](../../../docs/lld/web-ui.md) §6. The [trace prototype](../../web-ui/prototype/trace/index.html) holds a working reducer and layout to carry over.

**Blocked by:** 08: Reload or reconnect without losing the Run

**Status:** ready-for-agent

Scope limits, each lifted by a later ticket:
- Spinners, pulses, flowing rails and the loop dot are 11. Their static forms ship here.

- [ ] The 316 px panel shows on an opened Run only, drawn as hand-written SVG from `/meta`'s topology and the label table
- [ ] Only back-edges are drawn as edges; a skipped Step says "Not needed"
- [ ] All six states read without colour, and optional Steps have a dashed outline from the start
- [ ] A Step is done when the Run moves to a different Step or on `Done`, and a Pause marks only its own Step waiting
- [ ] A tool in flight shows on the Search Step, with source pills for count, cached and failed; an unknown tool shows its raw name
- [ ] A loop adds a "×2" badge, turns the back-edge amber, and resets the Steps between, except optional ones that ran
- [ ] Read postings shows a bar and "3 of 6 batches"
- [ ] Progress follows §6's weights, an active Step counts 35% (Read postings its batch fraction), `Done` snaps to 100%, and it never decreases
- [ ] The bar is amber while waiting and red on `Stopped`, with a line naming the live Step
- [ ] `fromLog` places the trace on a reload and reopen, with visit counts from `run_log`
- [ ] The panel keeps the live Step in view, and clicking a waiting Step scrolls to its Pause card
- [ ] Under about 900 px the panel becomes four band chips, the live-Step line and the bar
- [ ] Vitest covers: progress never decreases, loop reset, and a replay giving the same state as live
- [ ] Checked by hand through a Demo Run and a reload at each Pause, and at phone width
