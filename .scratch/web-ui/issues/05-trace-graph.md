# Trace graph

Type: prototype
Status: resolved
Assignee: smayankulkarni05
Blocked by: [Research: graph rendering and GSAP in React](02-research-graph-rendering-and-gsap.md)

## Question

How does the user-level trace graph show which tool or step the system is on, and what remains?

- The node set a user sees: all of the HLD §4 graph, or grouped by owner stage (`request_plan`, `collection`, `analysis`, `brief`) with the Pause nodes drawn as "waiting for you". The friendly label for each raw node name and each tool (`search_jobs` and the like), and how API calls (`ApiCalled`, per source, cached or not) appear on the Collection step.
- Node states and what each looks like: idle, active, done, failed, skipped, waiting on a Pause.
- Loops and branches: `broaden` back to `fetch_agent`, `clarify` back to `intake`, plan edit back to `plan`, critic back to `write_brief`. Drawn as a back-edge, a counter on the node ("Attempt 2"), or both.
- The fan-out of `batch_extract` as one node with an inline progress ring or bar from `ExtractProgress`, not per-branch nodes.
- The overall progress bar: what it measures (nodes passed, weighted by stage) and what it does on a loop.
- A finished or reloaded Run: whether the graph can be rebuilt from `get_run` (`run_log` and state) with no stored events, or the Controller must persist them. This settles the fog item on persisted event history.
- The renderer chosen from [Research: graph rendering and GSAP in React](02-research-graph-rendering-and-gsap.md).

Prototype the graph with a scripted event feed, reviewed in the browser by the agent. The resolution records the node and label table, the state model, the progress rule and the renderer, and links the prototype.

## Answer

Decided by the agent (the user delegated every decision on 2026-10-31) by building [the prototype](../prototype/trace/index.html): the real `RunEvent` shapes replayed through one pure reducer into a hand-written SVG animated by GSAP 3.15.0, with three scripted Runs (a happy path with one question and one critic revision, a widen-twice-then-ask Run, and a Run that fails during extraction) and three reopened Runs. Serve the folder over http to open it. It is throwaway; the reducer is the part worth carrying into the build.

**What the user sees: 14 steps in four bands, not 17 raw nodes.** The bands are the owner stages, and a label table in the UI merges plumbing nodes into one step, so the graph reads as what the system is doing rather than how it is wired.

| Band | Step (label) | Raw nodes | Optional |
|---|---|---|---|
| Understand | Read your request | `intake`, `clarity_check` | |
| | Ask you | `clarify` | yes, a Pause |
| | Plan the search | `plan` | |
| | Your approval | `plan_review` | a Pause |
| Collect | Search job boards | `fetch_agent`, `tools` | |
| | Filter postings | `collect`, `relevance` | |
| | Widen the search | `broaden` | yes |
| | Too few postings? | `low_data_review` | yes, a Pause |
| Analyse | Read postings | `batch_extract` | |
| | Tidy skill names | `normalise_skills` | |
| | Compute the numbers | `stats` | |
| Brief | Write the brief | `write_brief` | |
| | Check every claim | `critic` | |
| | Finish | `render` | |

- **Topology stays on the backend; labels stay in the UI.** The server's graph endpoint returns `{nodes: [{id, owner}], edges: [{source, target}]}` from `OWNERS`, `EDGES` and `CONDITIONAL`. The UI orders steps by owner band then node order, maps each edge through the label table, drops self-edges (the `fetch_agent` and `tools` loop) and `START`/`END`, and treats an edge to an earlier step as a back-edge. The prototype asserts the five back-edges this yields: `ask→read`, `approve→plan`, `widen→search`, `few→widen`, `check→write`. A node missing from the table should be a build-time test failure, so a new node can't silently go unlabelled.
- **The spine is the timeline, and only back-edges are drawn as edges.** Steps sit on a vertical rail in order; the rail segment into the live step is a flowing dashed blue line, and segments already passed turn green. Forward edges that skip a step (`read` to `plan` past `ask`) are not drawn: the skipped step shows "Not needed" instead.
- **Layout: a fixed vertical rail,** one 214 px-wide node per step, 22 px between nodes, back-edges bowed to the right (the panel is 316 px). The `Search` node is taller and holds source pills. This replaces the shell's 4-row placeholder, so the panel scrolls and keeps the live step in view.

**States, each readable without colour:** idle (hollow circle), active (spinner arc, pulsing ring, flowing rail), done (filled green circle with a drawn check), waiting for the user (amber, pause bars, slow ring, "Waiting for you to approve" and so on), failed (red cross, "Stopped. Resume retries it"), skipped (faded, dashed, "Not needed"). Optional steps have a dashed outline from the start. A step is done when the Run moves to a different step, or on `Done`; a Pause only ever marks its own step waiting.

**Tools and API calls.**
- A tool call shows on the `Search` step, not as its own node: while a call is in flight the step's line reads `Adzuna · "data engineer" p1`, and on `ToolReturned` it falls back to the last note.
- Per source, a pill under the step: filled blue with the count when live, hollow with "· cached" when from cache, red with a cross when failed. Tool names map `search_adzuna` to Adzuna and `search_usajobs` to USAJOBS; an unknown tool shows its raw name.

**Loops.** A step that runs again gets a counter badge ("×2"); the back-edge turns amber and a dot travels back along it. Steps between the target and where the Run was reset to idle with their notes cleared, but optional steps that ran (`ask`, `widen`, `few`) stay done so they are never marked skipped. The progress bar never goes backwards.

**Fan-out.** `batch_extract` is one step, "Read postings", with a bar and "3 of 6 batches" from `ExtractProgress`; the bar turns green when done. No per-branch nodes, as no event carries a branch ID.

**The progress bar** is a weighted share of the main path: Read your request 1, Plan 1, Your approval 0.5, Search 3, Filter 1, Read postings 4 (by batch fraction), Tidy 1, Compute 1, Write 2, Check 1, Finish 0.5. Optional steps weigh 0. An active step counts 35% of its weight (the extraction fraction for Read postings), a done step counts all of it, and `Done` snaps to 100%. It never decreases on a loop. It turns amber while waiting on a Pause and red on `Stopped`. Under the bar, a line names the live step ("Search job boards…", "Waiting for you: Your approval", "Stopped at …").

**Reload and reconnect.** The reducer is pure and the buffer replays from the start (see [Research: delivering Run events over FastAPI SSE](01-research-sse-over-fastapi.md)), so on reconnect the client applies the buffered events at once with no animation and then goes on live. Checked: replaying the events gives an identical state.

**A reopened Run needs no stored events,** which settles the fog item: rebuild from `get_run`. ([Web API and hosting](03-web-api-and-hosting.md) later refined the source from State fields to `run_log`, so one rule also serves a reload mid-Run. No events are stored either way.) The status, `stopped_at` or the pending Pause kind place the cursor; steps before it are done; the optional steps use State fields: `questions` non-empty means Ask you ran, `len(broadened_plans)` is how many times Widen ran (Search shows ×N+1), and `low_data_decision` set means the low-data Pause ran. Checked on a done, a failed and a paused Run. What a reopened Run loses: tool and source lines, per-step notes and attempt detail. The trace shows the route and outcome, which is all the shell's reopened Runs need. No Controller change.

**Narrow screens** use the same state: four stage chips (done, active, waiting or failed) plus the live-step line and the progress bar.

**Motion shown here, for [Motion with GSAP](09-motion-with-gsap.md) to formalise:** spinner rotation, pulse ring, rail dash flow, a drawn check (`DrawSVGPlugin`), a dot along the back-edge (`MotionPathPlugin`), a counter pop, a failure shake, bar width tweens and smooth scrolling to the live step. State drives every tween. Under reduced motion no repeating tween runs (3 live loops became 0 in the check) and every change is a plain state change. Checked in the browser pane: no console errors.

**Renderer:** hand-written SVG, as [Research: graph rendering and GSAP in React](02-research-graph-rendering-and-gsap.md) recommended. The prototype is vanilla JS; the build uses React with one scoped `useGSAP`, and a reducer that is this one rewritten in TypeScript.

**Not settled here:** how the real UI places the Pause card relative to its waiting step ([Live Run view](06-live-run-view.md)), and the full animation inventory and timings ([Motion with GSAP](09-motion-with-gsap.md)).
