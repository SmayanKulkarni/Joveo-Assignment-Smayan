# Trace graph

Type: prototype
Status: open
Assignee: none
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
