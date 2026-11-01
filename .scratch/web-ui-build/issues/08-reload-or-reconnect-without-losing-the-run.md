# 08: Reload or reconnect without losing the Run

**What to build:** a user can reload, open a Run in a second tab, lose the connection, or come back after a server restart, and the page rebuilds what happened and carries on live. A Run reopened from history shows its route and notes with no stored events. Spec: [Web UI LLD](../../../docs/lld/web-ui.md) §7 (`fromLog`, Connecting), §5 (what an opened Run shows first).

**Blocked by:** 03: Answer a Pause and carry on; 07: See the Run think and search

**Status:** done

- [x] `live_from` reports the attached handle's `log_start`, or null with none attached
- [x] `fromLog` groups `run_log[:live_from]` into turns by consecutive Step, or all of it with no live handle
- [x] A `collect` line implies `search` ran before it, and a `normalise_skills` line implies `postings` did
- [x] Each status opens as §5's table says, including a `running` Run live elsewhere, which polls every 3 s and offers no Stop
- [x] A reload mid-Run shows no duplicated or missing turns across the `live_from` boundary, including after a resume
- [x] `onopen` resets to the stream's base, while the `texts` map survives, so a dropped connection keeps text already on screen
- [x] `animate` stays false until `caught_up`, and on any reopened Run
- [x] "Some live text wasn't kept" appears only when the active turn could have streamed and was reached by replay
- [x] "Reconnecting…" shows after a 2 s grace at `readyState` 0
- [x] `readyState` 2 fetches `RunDetail` and rebuilds, including after a server restart mid-Run
- [x] Two tabs on one live Run both stream, and closing one leaves the Run and the other tab running
- [x] Vitest covers `fromLog` per status and its inferences, and a reset keeping `texts`
- [x] `pytest` covers `live_from`, and `caught_up` coming before any token on attach
- [x] Checked by hand: reload at each Pause and mid-search, a second tab, and a server restart mid-Run
