# 12: Browser smoke, one live Run, delete Streamlit

**What to build:** proof that the whole UI works end to end, in a real browser on a Demo Run and by hand on a real Run, after which the web UI replaces Streamlit. Spec: [Web UI LLD](../../../docs/lld/web-ui.md) §12, §13 pass 8.

**Blocked by:** 04: Edit the Search Plan; 05: Read the Market Brief; 06: Find earlier Runs in the sidebar; 09: Stop and Resume a Run; 11: Motion

**Status:** ready-for-agent

If 11 is dropped for time, this ticket waits on 10 instead.

- [ ] A smoke script drives a Demo Run in a real browser: start, each Pause including a refused edit, reload mid-Run, stop and resume, `Done`, Brief
- [ ] It uses the installed Edge through Playwright, with no browser download or repo dependency, and isn't collected by `pytest`
- [ ] One real Run by hand through `scout serve`, with notes on anything that reads badly, fixed or raised
- [ ] A fresh production build serves with a single `uv run scout serve`
- [ ] `streamlit_app.py`, `streamlit_bridge.py` and the `streamlit` group are deleted, and `uv lock` is refreshed
- [ ] `event_line`'s docstring in the CLI and "shared by every client" in the Pause text helpers no longer mention what's gone
- [ ] The CLI still works: `pytest` passes in full, and `npm test` passes
- [ ] `docs/lld/web-ui.md` still matches what was built, with any change made during the build written back
