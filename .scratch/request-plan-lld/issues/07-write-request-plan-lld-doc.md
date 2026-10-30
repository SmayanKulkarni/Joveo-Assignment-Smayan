# Write docs/lld/request-plan.md

Type: task
Status: resolved
Assignee: smayankulkarni05
Blocked by: 01, 02, 03, 04, 05, 06

## Question

Is `docs/lld/request-plan.md` written, with per-pass build checklists and future-scope entries, and with the upstream ⏳ Request & Plan items closed?

## Answer

Yes. [docs/lld/request-plan.md](../../../docs/lld/request-plan.md) is written, with checklists for passes 1 and 2 and a Request & Plan section in `future-scope.md`. The ⏳ items in Kernel §4, Runtime §1, §5 and §17, Gateway §3 and HLD §12 are closed.

No code changed. `kernel/types.py`, `gateway/types.py` and `State` still have the old shapes until step 1 of the pass 1 checklist.

Decisions made while writing, beyond the tickets:
- **Runtime comes first in the build,** since this stage needs `runtime/deps.py`, `runtime/pause.py` and the stub `types.py`.
- **Future scope gained three items:** `focus` shaping the Search Plan, fetching Adzuna's per-country category list, and multi-country Runs.
- **Unproven until the live smoke:** the 0.5 clarity cut on real requests.
