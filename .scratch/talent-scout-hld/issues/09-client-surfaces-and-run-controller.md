# Which clients exist, and how do they talk to the graph?

Type: grilling
Status: resolved

## Question

Which user-facing clients does the core ship, and what seam keeps the later infra phase from being a rewrite?

## Answer

Resolved during charting.

- **CLI is the core client**: handles all three Pauses, `--focus` flags, `--resume`, streamed progress.
- **Streamlit** is an optional recommended-tier client; its rerun-per-interaction model fits checkpointing (each rerun resumes the thread).
- A **Run Controller** (start / resume / stream events / get state) is the only thing clients call; none touch the graph directly. The CLI, Streamlit and the future API worker all sit on it, which makes the infra shell an addition rather than a rewrite.
