# Frontend build and verification

Type: grilling
Status: open
Assignee: none
Blocked by: [Web API and hosting](03-web-api-and-hosting.md)

## Question

How is the frontend laid out, built, served and checked, so that someone can build it step by step?

- `web/` layout, the package manager and pinned versions (Vite, React, TypeScript, `gsap`, `@gsap/react`), and the state approach for the Run reducer (plain `useReducer` and context, or one small store).
- The `web` dependency group in `pyproject.toml` (FastAPI, uvicorn) and how `scout serve` fits `[project.scripts]` beside the `scout` CLI.
- Development: Vite's dev server proxying `/api` to the Python server, and the demo mode as the default way to work.
- Production: the built `web/dist` served by FastAPI, with a single `uv run scout serve`.
- Verification: unit tests for the event reducer with scripted event feeds (Vitest), API tests with FastAPI's test client over the stub graph, and one browser smoke through a stub Run (start, each Pause, Done). The skip-list: no pixel tests.
- Deleting Streamlit (`streamlit_app.py`, `streamlit_bridge.py` and the `streamlit` group) and when.
- A build checklist in passes, each leaving one check behind.

Resolution is the layout, the commands and the checklist.
