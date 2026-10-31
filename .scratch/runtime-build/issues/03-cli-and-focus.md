# 03: CLI and `--focus`

**What to build:** a developer drives a whole Run from the terminal: `scout run "<request>" [--focus dim ...]`, answering each Pause, then `scout resume` and `scout show` to pick it up or read it later. `Ctrl-C` leaves a resumable Run. `--focus` values land in the checkpoint. Spec: [Runtime LLD](../../../docs/lld/runtime.md) §12, §16 pass 1 steps 8-9 and pass 2 step 1.

**Blocked by:** 02: Run Controller and the skeleton proof.

**Status:** in-progress, waiting on the hand Ctrl-C check

- [x] `scout` entry point with `run`, `resume [thread_id]` and `show <thread_id> [--log]`, prompts run outside the event loop, and exit codes as in §12
- [x] A shared plain-text renderer for each Pause payload, used by the CLI and later Streamlit
- [x] `edit` opens `$EDITOR` (`notepad` fallback) on the Search Plan as JSON, and re-opens with the error on top if validation fails
- [x] `resume` with no ID lists resumable Runs and prompts, and with an ID handles each status as in §12
- [x] `show` is read-only and prints per status, and `--log` adds the `run_log` table
- [x] Test: scripted `input` drives `scout run` through the stub Pauses, a bad answer re-asks the same Pause, and `resume` and `show` output matches each status
- [x] Test: `--focus` is rejected for unknown values, and the chosen values are in `State.focus` in the checkpoint
- [ ] `Ctrl-C` checked by hand on Windows, at a prompt and during a live Run
- [x] One live smoke script (not in CI) runs the same flow with the real `check_balance`

**Notes:** menu letters are `a`/`e`/`r`/`x` for plan review and `b`/`c`/`x` for low data review. `main` sets stdout to replace unencodable characters, because the live smoke crashed on `✓` with piped output on Windows. `Ctrl-C` is the one open item: it needs a person at a Windows terminal, at a prompt and during a live Run (`python scripts/smoke_cli.py` gives a Run to interrupt).
