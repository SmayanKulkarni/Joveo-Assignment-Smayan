# 04: Streamlit client

**What to build:** a disposable web page over the Run Controller: start a Run with a focus selection, answer each Pause in a form, reload at a Pause and carry on, see failed Runs and resume them, and download the Brief. No Controller changes. Spec: [Runtime LLD](../../../docs/lld/runtime.md) §13, §16 pass 2 step 2.

**Blocked by:** 02: Run Controller and the skeleton proof, 03: CLI and `--focus` (for the shared Pause renderer and `--focus`).

**Status:** done

Run it with `uv run --group streamlit streamlit run src/talent_scout/clients/streamlit_app.py`. Not exercised by hand: the failed-Run view and "Run in progress" on reload, since a stub Run is too fast to catch either.

- [x] A `streamlit` dependency group, a bridge holding one Controller on a background loop for the process lifetime, and the thread ID in `st.query_params`
- [x] No ID shows the request box, the focus multiselect and a table of Runs linking to each; an ID renders from `get_run` by status
- [x] One form per Pause kind, a JSON `text_area` for `edit`, and `InvalidAnswer` shown above the same form
- [x] Node lines in `st.status` while a Run is live, and "Run in progress" with a Refresh button on reload
- [x] `done` shows the Brief with JSON and Markdown downloads
- [x] Checked by hand through a stub Run: start, each Pause form, a bad answer, reload at a Pause, and download. No automated tests.
