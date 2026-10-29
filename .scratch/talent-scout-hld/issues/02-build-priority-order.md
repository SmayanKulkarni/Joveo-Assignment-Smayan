# What is the build priority order when time runs short?

Type: grilling
Status: resolved

## Question

In what order are requirement tiers built, given a deadline of Mon 2 Nov 2026, 9:00 AM, and where does the infra layer sit?

## Answer

Resolved during charting.

1. Must-haves (assessment minimum bar)
2. Recommended (Send map-reduce, plan-approval and low-data Pauses, retries/fallbacks, malformed-output recovery, CLI/Streamlit, `--focus` flags)
3. Streaming progress
4. Infra shell (API, queues, workers, concurrency, threading, MiniStack): explicitly a **future phase** after core requirements are done
5. Critic pass
6. Long-term memory

The core graph must never depend on the infra shell; the shell wraps it later through the Run Controller seam (see [Client surfaces and the Run Controller seam](09-client-surfaces-and-run-controller.md)).
