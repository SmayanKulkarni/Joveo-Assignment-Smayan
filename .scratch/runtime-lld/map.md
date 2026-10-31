# Runtime and CLI LLD

Label: wayfinder:map
Parent: [Talent Market Scout: HLD](../talent-scout-hld/map.md) (components G and H in [docs/HLD.md](../../docs/HLD.md) §3, §8)

## Destination

`docs/lld/runtime.md`: an LLD of Runtime and Clients precise enough to build straight from, covering pass 1 (wiring, SQLite, registry, Run Controller, Pause protocol, resume guard, CLI, stub-node skeleton), pass 2 (`--focus` plumbing, Streamlit's mapping onto the Run Controller) pass 3 (event model) and how pass 6 opens the Store, with nothing left to decide. Building the code is a separate effort after this map.

## Notes

- Domain: Runtime wires and runs the graph and owns threads and the registry; Clients call only the Run Controller. Vocabulary: `GLOSSARY.md`. Spec: `Joveo_Talent_Market_Agent- Assessment.pdf`. Deadline Mon 2 Nov 2026, 9:00 AM, so this map stays lean.
- Fixed upstream: [docs/lld/kernel.md](../../docs/lld/kernel.md) §7 (routing), §8 (`owned()`), §10 (persistence rules), §12 (`check_balance`), [docs/lld/gateway.md](../../docs/lld/gateway.md), HLD §8, [Research: LangGraph persistence and resume](../talent-scout-hld/issues/15-research-langgraph-persistence-and-resume.md).
- Skills: `langchain-router` first for any framework question (per `CLAUDE.md`); `grilling` + `domain-modeling` for grilling tickets.
- Standing preferences: inherited from the Kernel map (Pydantic v2 everywhere, `uv`, Python 3.12, `src/talent_scout/`, `pytest`, root `.env`).
- Scope rules (decided at charting):
  - **Boundary with stages.** Runtime owns the export contract, dependency handover, the Pause envelope, the wiring table from HLD §4 and a stub-node skeleton. Stage LLDs own node bodies and each Pause's payload and answer fields.
  - **Dependencies.** Each stage exports `make_nodes(deps: Deps) -> dict[str, Node]` plus plain router functions, closing over a frozen `Deps(tiers, jev, gateway, settings)`. No `context_schema`.
  - **Async throughout.** Async Run Controller on `AsyncSqliteSaver`, `AsyncSqliteStore` and `astream`; the CLI calls `asyncio.run`; Streamlit bridges in its own layer.
  - **Storage.** Checkpointer and registry share `.cache/runs.sqlite` (setting `runs_db`), separate from `gateway.sqlite`. The registry is a plain `runs` table, not a Store namespace, and the Store is opened only when preferences land (pass 6), per [Run Controller API and wiring](issues/02-run-controller-and-wiring.md).
  - **Run status.** The registry stores `running | paused | done | aborted | failed`, thread ID, request summary and updated time. It is an index: `get_state` is the truth and disagreements reconcile on read, so no heartbeat. A killed Run stays resumable.
  - **Resume guard.** A per-thread OS-level lock: a stdlib SQLite connection holding `BEGIN IMMEDIATE` on `.cache/locks/<thread>.lock`. A second process gets an immediate "this Run is open elsewhere" error. Confirmed by the research ticket.
  - **Pause envelope.** Every `interrupt()` carries `Pause(kind, payload)`, `kind` being `clarify | plan_review | low_data_review`. The answer is a per-kind model the Controller validates before `Command(resume=...)`, so a bad answer re-prompts. Clients render by `kind`.
  - **CLI.** Stdlib `argparse`: `scout run "<request>" [--focus dim ...]`, `scout resume [thread_id]` (lists resumable Runs with no ID), `scout show <thread_id>`. The Market Brief is printed and written as JSON and Markdown to `runs/<thread_id>/`.
  - **Events (pass 3).** Clients get a chat-assistant-style live view: LLM tokens as they arrive, tool and API calls as they happen, and a reasoning display. The event stream yields a `RunEvent` union and clients never see LangGraph chunks. The exact events and their sources are decided in [Clients flow](issues/03-clients-flow.md), after [Research: live streaming sources](issues/05-research-live-streaming-sources.md).
  - **Streamlit is disposable.** A simple web UI is future scope, so Streamlit stays a thin client that shapes nothing in Runtime.
- On 2026-10-31 the user told the agent to make every remaining decision itself and finish the map. Tickets 06 and 07 were decided by the agent, and each says so.

## Decisions so far

<!-- one line per closed ticket -->

- [Research: async persistence and the resume guard](issues/01-research-async-persistence-and-guard.md): the lock-file guard holds, including after a hard kill; saver and Store share one file on separate connections; `Pause.payload` loses its class across processes unless concretely typed; `setup()` needs retry on a fresh file, and registry read-then-write needs `BEGIN IMMEDIATE`.
- [Research: live streaming sources](issues/05-research-live-streaming-sources.md): the chat-style view is practical; `messages` mode needs two fixes in `kernel/llm.py` first; reasoning is optional per turn; structured output streams JSON fragments and stays provisional until the node finishes; closing a stream cancels the Run.
- [Run Controller API and wiring](issues/02-run-controller-and-wiring.md): the Controller owns the graph task and hands out a `RunHandle` with an in-memory event buffer; the registry is a `runs` table written after the checkpoint and reconciled on read; `Pause` is a discriminated union by kind; the full graph compiles from day one with stubs for missing stages; the skeleton proves resume with a kill-and-resume test across processes.
- [Clients flow](issues/03-clients-flow.md): `rich` CLI with `$EDITOR` plan edits and `Ctrl-C` cancelling to a resumable Run; `RunEvent` union with tokens only from `fetch_agent` and a new `tasks` stream mode to verify; tokens stay out of the replay buffer; Streamlit is a thin client with no Controller changes.
- [Write docs/lld/runtime.md](issues/04-write-runtime-lld-doc.md): the LLD is written and the Kernel, Gateway, HLD and future-scope docs agree with it; the `tasks` mode passed an offline check, which also removed the need for a custom extraction signal.
- [Opening the Store](issues/06-opening-the-store.md): from pass 6 the Controller opens it on `runs_db` on its own autocommit connection, and nodes reach it through `runtime.store`, not `Deps`.
- [Bring the LLD in line with the code](issues/07-bring-the-lld-in-line-with-the-code.md): three stale details fixed in the doc, the code was right each time, and nothing else in HLD §3's Runtime row is undecided.

## Not yet specified

Nothing: the destination is reached.

## Out of scope

- Infra shell internals: only the seam at the Run Controller is stated here.
- Node bodies, Pause payload and answer fields, what each `--focus` value changes: stage LLDs.
- What the Store holds and which nodes read it: Long-term memory LLD.
- Writing the Runtime and CLI code: separate build effort after this map.
