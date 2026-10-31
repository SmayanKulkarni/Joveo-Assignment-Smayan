# Bring the LLD in line with the code

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by: 06

## Question

The Runtime build and the later stages have landed since `docs/lld/runtime.md` was written. Where does the doc no longer describe the code, and is anything else in HLD §3's Runtime row undecided?

## Answer

Compared the LLD with `runtime/graph.py`, `deps.py`, `guard.py`, `registry.py`, `pause.py`, `events.py` and `controller.py`. The code was right each time, so only the doc changed:

| Section | The doc said | The code does |
|---|---|---|
| §3 | `Deps` has four fields | A fifth, `stub_stages`, lets tests run a landed stage as its stub |
| §4 | `relevance` has three targets | A fourth, `stats`, because `fan_out` sends an empty Sample there |
| §6 | `cancel()` always writes `failed` | A Run with no checkpoint yet has nothing to rerun, so it writes `aborted` |

Also added from [Opening the Store](06-opening-the-store.md): §1, §4, §11, §16 and §17.

Nothing else in the row is undecided: wiring, checkpointer, registry, Run Controller, event stream, Pause protocol and guard are all specified and built.

The Runtime tests gave 66 passed on three runs in a row. An earlier run had 2 failures in `test_skeleton_proof.py`, while another session was part-way through its Brief edits. The 2 passed on an immediate rerun, so they weren't investigated further. No code changed here.
