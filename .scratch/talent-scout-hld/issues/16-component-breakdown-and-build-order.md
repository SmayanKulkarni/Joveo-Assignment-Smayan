# Component breakdown and build order

Type: grilling
Status: open
Blocked by: 12, 13, 14, 15

## Question

Into which components does the system split (each to become its own LLD/build effort), what does each own (responsibility, boundary, the slice of state it reads and writes, its seams to neighbours), and in what order are they built under [What is the build priority order?](02-build-priority-order.md)?

Inputs: the graph in [What is the node-level graph shape?](06-graph-shape.md), the decisions in tickets 01–11, and the research findings from tickets 12–15. The breakdown should also place the infra shell (API, queues, workers, concurrency, MiniStack) as a future-phase component with its seam to the Run Controller.
