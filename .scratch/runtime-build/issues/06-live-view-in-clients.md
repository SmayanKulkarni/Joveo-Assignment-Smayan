# 06: Live view in the clients

**What to build:** the CLI and Streamlit show the chat-assistant-style live view: prose tokens and dim reasoning from `fetch_agent`, a spinner for structured nodes, an extraction count, and a line per tool and API call. Spec: [Runtime LLD](../../../docs/lld/runtime.md) §12 (live view), §13, §16 pass 3 step 4.

**Blocked by:** 03: CLI and `--focus`, 04: Streamlit client, 05: Event stream.

**Status:** done

- [x] The CLI follows the §12 live-view table, and the spinner stops on the first `Token` or `Reasoning` and restarts on the next `NodeStarted`
- [x] Streamlit adds tool and API lines to `st.status` and `st.progress` for extraction, and ignores tokens and reasoning
- [x] Test: the CLI's rendering of a scripted event sequence, including a turn with no reasoning
- [x] One live run (not in CI) to check how the view reads
- [x] Check whether `deepseek/deepseek-v4.1-flash` sends readable reasoning, and record the answer in LLD §10
