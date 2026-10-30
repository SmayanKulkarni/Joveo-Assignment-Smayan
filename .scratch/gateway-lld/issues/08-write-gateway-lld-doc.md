# Write docs/lld/gateway.md

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01, 02, 03, 04, 05, 06, 07

## Question

Write `docs/lld/gateway.md` from the resolved tickets and the map's Notes: module layout, query interface, Adzuna and USAJOBS clients and mappers, L1, budget guard, replay, L2, expiry and sweep, settings rows, test seams, and the build checklist per pass. Gist and link each decision to its ticket; introduce no new decisions. Fill Kernel §15's Jobs APIs row by linking here. Include `coalesce` and the source-choice rule.

## Answer (2026-10-30)

Written: [docs/lld/gateway.md](../../../docs/lld/gateway.md). Kernel §15's Jobs APIs row now links to it, and [future-scope.md](../../../docs/lld/future-scope.md) has a Gateway section. No API calls spent.

Details the tickets left open, settled while writing, none changing a ticket's decision:
- **`SourceRejected`, and no `raise_for_status()`.** Confirmed on `httpx` 0.28.1: its message includes the full URL, so a 401 would put `app_id` and `app_key` in logs and traces. The credential rule in [Adzuna client and mapper](03-adzuna-client-and-mapper.md) needs a plain exception that carries only status and body.
- **`ADZUNA_CURRENCY` lives in `gateway/types.py`,** not the Adzuna client as [Adzuna client and mapper](03-adzuna-client-and-mapper.md) says, because the `Fetch` validator needs it and the client imports `Fetch`.
- **Series `8999` gets an override into `maintenance-jobs`.** It's the one entry of 822 in the code list whose `JobFamily` (`8800`) isn't its first two digits plus `00`.
- **Replay rows are written as served,** after the close-date filter, so a replay returns what the recording Run returned. They go in a `jobs` table on the Kernel's `Replay`.

Noted, not changed:
- [L2 store, expiry and sweep (pass 2)](07-l2-store-expiry-and-sweep.md) writes every L2 answer to the replay file, including a failure fallback's partial page. A replay of that Fetch then reports `replay` with no `failures[adzuna]`, so the "one source failed" Caveat doesn't repeat.
- The L2 radius check also applies to a country-wide `via`, so a small `radius_km` on one costs an extra call. Listed as a known limit.
- A blank Adzuna description isn't a drop, unlike USAJOBS, so it could over-merge in `coalesce`. Not seen in the 100 results sampled.
