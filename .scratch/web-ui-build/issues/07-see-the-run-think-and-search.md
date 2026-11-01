# 07: See the Run think and search

**What to build:** a running Run reads as a live chat-style stream. Text streams in as the model writes it, a tool call shows a loading card that resolves to its result, extraction shows a bar, and finished turns tuck themselves away. Spec: [Web UI LLD](../../../docs/lld/web-ui.md) §7 (turns, blocks, State, auto-scroll, accessibility), §12 (contract).

**Blocked by:** 02: Start a Run and watch it reach a Pause

**Status:** done

Scope limits, each lifted by a later ticket:
- A reconnect may still lose streamed text, and a reload shows no history (08).
- Tokens are plain text with no caret animation (11).

- [x] A `NodeStarted` whose Step differs from the current turn's opens a new turn; `fetch_agent` and `tools` stay in one, and a loop opens another
- [x] The active turn is expanded; a finished one collapses to its check, label and last note, and expands on click
- [x] Every event in §7's table has its effect, through one pure reducer
- [x] `Reasoning` is a closed `<details>`, created on the first fragment, so none means no block
- [x] Drafting lines use §7's phrases, end on the first token or `NodeDone`, and JSON fragments are never shown
- [x] Tool cards pair first-in-first-out by name, and `ApiCalled` sets the source pill: count, "cached" or "failed"
- [x] A card still open at `Stopped` reads "Interrupted"
- [x] Events flush once per frame, with a 250 ms timeout for hidden tabs, and finished turns are `memo`ised
- [x] Once `done`, all turns fold under a closed "How this Run went"
- [x] Auto-scroll sticks within 80 px of the end, and scrolling up shows "Jump to latest", reading "Waiting for you" when a Pause arrived off-screen
- [x] The stream is `role="log"` with `aria-live="off"`, a polite region announces Step changes, Pauses and endings, and a Pause heading takes focus when stuck to the bottom
- [x] A pytest compares a Demo Run's events and `/meta` with the committed `demo-run.json`, and Vitest feeds that file to the reducer
- [x] Vitest covers: the feed's end state, one batch equals one by one, tool pairing, and no block for absent reasoning
- [x] Checked by hand through a Demo Run, and one fast token stream stays smooth
