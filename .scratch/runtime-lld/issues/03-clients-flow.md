# Clients flow

Type: grilling
Status: resolved
Assignee: smayankulkarni05
Blocked by: none

## Question

How do the CLI and Streamlit behave on top of the Run Controller?

- How each Pause kind renders and takes an answer, including re-prompting on a bad answer.
- What `scout resume` lists, what `scout show` prints, and what a stopped Run tells the user.
- Progress display before and after the pass 3 event stream.
- The live view: the exact `RunEvent` union, how tokens, tool and API calls and reasoning display, which nodes show tokens versus a status line (structured JSON and parallel extraction may not read well), and whether the terminal UI needs a library such as `rich`.
- Streamlit's mapping: thread ID in the URL, rerun per interaction, bridging to the async Controller.

## Answer

Decided by grilling.

- **Layout.** `clients/cli.py`, `clients/streamlit_app.py`, `clients/streamlit_bridge.py`, and `scout` as a `[project.scripts]` entry point. The two clients share only `clients/pauses.py`, the plain text formatting of each Pause payload.
- **Terminal.** `rich` for output from pass 1 (spinner, dim reasoning, tables, Markdown), plain `input()` for prompts.
- **Pauses in the CLI.** Rendered by `kind`.
  - `clarify`: print the questions, take a typed answer to each in turn.
  - `plan_review`: print the Search Plan, take a one-letter choice: approve / edit / reject (then ask for feedback) / abort.
  - `low_data_review`: print the counts, take a choice: broaden / continue / abort.
  - `InvalidAnswer(errors)` prints the errors and re-asks the same Pause, with no attempt cap.
  - `Ctrl-C` at a prompt leaves the Run `paused` and exits with "resume with `scout resume <id>`".
- **`edit` at `plan_review`.** The CLI writes the Search Plan as JSON to a temp file and opens `$EDITOR` (`notepad` as the Windows fallback). It validates on save against the plan model, and on an error re-opens the editor with the error at the top.
- **`Ctrl-C` during a live Run.** Calls `handle.cancel()` (`failed` / `cancelled`, lock released), prints "Stopped at <node>. Resume with `scout resume <id>`" and exits 130. There is no detach, because the Controller dies with the CLI process.
- **`scout resume`.**
  - No ID: a table of `paused` and `failed` Runs, newest first, with `#`, thread ID, status, summary, relative updated time, and a hint (pending Pause kind or stopped node). Prompt for a number or ID, first row on Enter. "No resumable Runs" if empty.
  - With an ID: `paused` re-shows its Pause; `failed` prints "Stopped at <node>: <error>. Retrying." and streams; `done` or `aborted` prints "Run already finished, see `scout show <id>`"; a locked Run prints "This Run is open elsewhere".
- **`scout show <thread_id>`.** Read-only, never locks. A header (ID, status, summary, updated time), then by status: `done` prints the Market Brief Markdown and the `brief.md` path; `paused` prints the Pause read-only plus the resume hint; `failed` prints the stopped node, error and resume hint; `aborted` prints the abort reason from `run_log`. `--log` also prints `run_log` as a table.
- **Progress before pass 3.** One line per `NodeDone`, which also carries `notes: list[str]`: the messages of the `run_log` entries that node appended, found by diffing the log length in the `updates` chunk. Raw node names, no friendly labels. Example: `✓ relevance — 38 of 142 Postings relevant (route: enough)`.
- **Live view (pass 3).**
  - `fetch_agent` streams prose tokens, plus dim reasoning when it exists.
  - Structured nodes (`clarity_check`, `plan`, `broaden`, `write_brief`) show a spinner "drafting <node>…" plus dim reasoning. JSON fragments are never shown, and there is no partial-field parsing.
  - `batch_extract` shows only a count, "extracted 37/142".
  - Each tool and API call gets one line when called and one when done.
  - Jev and plain-code nodes get nothing beyond the `NodeDone` line.
- **`RunEvent`.** A discriminated union of Pydantic models in `runtime/events.py`:
  - `NodeStarted(node)` from `tasks` mode, and only once for `batch_extract`.
  - `NodeDone(node, notes)` from `updates`.
  - `Token(node, text)` from `messages`, `fetch_agent` only.
  - `Reasoning(node, text)` from `messages` via `content_blocks`, dropped for parallel branches.
  - `ToolCalled(name, summary)`, `ToolReturned(name, summary)`, `ApiCalled(source, cached, count)`, `ExtractProgress(done, total)` from custom events.
  - `Paused`, `Done`, `Stopped` from the Controller, as decided in [Run Controller API and wiring](02-run-controller-and-wiring.md).
  - No event carries a branch ID.
- **`stream_mode` gains `"tasks"`.** This adds to the modes fixed in Run Controller API and wiring. `tasks` was not part of [the streaming research](05-research-live-streaming-sources.md), so the pass 3 build must check that interrupts still behave with it.
- **Custom event emitters.** The guarded `emit()` lives in `kernel/`. The `tools` executor emits `ToolCalled` and `ToolReturned` with its own summaries, the Gateway emits `ApiCalled` per source once the source call finishes, and `batch_extract` emits nothing: the Controller counts its task starts and `updates` chunks, as settled in [Write docs/lld/runtime.md](04-write-runtime-lld-doc.md), which replaced a "one done" signal. Stages emit plain dicts with a `type` key, and the Controller maps them to `RunEvent` and drops unknown types with a log line, so Kernel and stages never import Runtime.
- **Replay buffer.** `Token` and `Reasoning` go only to live subscribers, never into the 5,000-event buffer. A client attaching mid-Run gets every node, tool and API line, and tokens from then on.
- **Streamlit stays thin and disposable.** A simple web UI is future scope and will replace it, so Streamlit gets no Controller changes and no event types of its own. It renders a subset of what the CLI does.
  - **Bridge.** `st.cache_resource` holds a background thread running an event loop, with one `RunController` open on it for the process lifetime. A sync wrapper uses `asyncio.run_coroutine_threadsafe`. A subscriber coroutine feeds a `queue.Queue` that the script reads.
  - **Pages.** The thread ID lives in `st.query_params["thread"]`. With no ID: a request box, a focus multiselect, and a table of Runs linking to `?thread=<id>`. With an ID: render from `get_run`, so `paused` shows its form, `failed` shows the error and a Resume button, `done` shows the Brief with JSON and Markdown downloads.
  - **Live view.** Node, tool and API lines in `st.status`, and `st.progress` for extraction. Tokens and reasoning are ignored.
  - **Pauses.** One `st.form` per kind, with a JSON `text_area` for `edit`. `InvalidAnswer` shows `st.error` above the same form.
  - **Cut on purpose.** No `attach()`, no Cancel button, no token placeholder. Reloading a running Run shows "Run in progress" with a Refresh button until it reaches a Pause or finishes. Closing the tab doesn't stop the Run, since the Controller owns the task.
