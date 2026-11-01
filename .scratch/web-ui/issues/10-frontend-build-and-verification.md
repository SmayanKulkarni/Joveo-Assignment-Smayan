# Frontend build and verification

Type: grilling
Status: resolved
Assignee: smayankulkarni05
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

## Answer

Decided by the agent (the user delegated every decision on 2026-10-31). The pins were installed together in a scratch project, where `tsc`, `vite build` and `vitest run` passed, with a `<StrictMode>` GSAP component in the build, on Node 22.14.0 and npm 10.9.2.

**Package manager and pins.** npm, which needs no install, with a committed `package-lock.json` and exact versions: `react` and `react-dom` 19.3.1, `gsap` 3.15.0, `@gsap/react` 2.1.2; dev: `vite` 8.3.5, `@vitejs/plugin-react` 6.1.2, `typescript` 7.0.2, `vitest` 5.0.5, `@types/react` and `@types/react-dom` 19.3.0.

**No router, store or CSS library.** Two routes need about 15 lines over `history.pushState` and `popstate`. Each Run's state is one `useReducer` in `useRun`, and the sidebar's is one `useRuns`, with a small context only to let the page ask the sidebar to refetch. Plain `styles.css` with custom properties, lifted from the shell prototype.

**`web/` layout.**
```
web/
  package.json  package-lock.json  index.html  vite.config.ts  tsconfig.json
  src/
    main.tsx  App.tsx  router.ts  styles.css  motion.ts
    api/      client.ts (fetch, refusal shape)  stream.ts (EventSource lifecycle)  types.ts
    run/      steps.ts (label table, weights)  reducer.ts  fromLog.ts  useRun.ts  RunPage.tsx  Stream.tsx  Turn.tsx  ToolCard.tsx
    pause/    PauseCard.tsx  ClarifyForm.tsx  PlanReviewForm.tsx  PlanEditor.tsx  LowDataForm.tsx
    brief/    BriefView.tsx  Evidence.tsx  RunNotes.tsx
    trace/    TracePanel.tsx  TraceStep.tsx  ProgressBar.tsx  StageStrip.tsx
    sidebar/  Sidebar.tsx  useRuns.ts
    composer/ Composer.tsx
    test/     reducer.test.ts  steps.test.ts  demo-run.json
```

**Types are hand-written in `api/types.ts`,** kept honest by a contract check rather than a generator. SSE events aren't in FastAPI's OpenAPI anyway. A pytest runs a Demo Run and compares its events and `/meta` with the committed `web/src/test/demo-run.json`, which the Vitest suite feeds to the reducer. A backend shape change fails pytest, and regenerating the file then fails the TypeScript side.

**Python dependencies.** `fastapi==0.162.0` and `uvicorn==0.54.0` join the main `dependencies`, not a group. The ticket suggested a `web` group, but `uv run` only includes `dev` by default, so a group would break the required single `uv run scout serve`, and this is now the product's main client. `scout serve` is a subcommand of the existing script, with no new `[project.scripts]` entry. `.gitignore` adds `web/node_modules/` and `web/dist/`.

**Development.**
```bash
uv run scout serve --demo
npm --prefix web run dev
```
Vite runs on 5173 with `server.proxy["/api"] = {target: "http://127.0.0.1:8000", changeOrigin: false}`. The string shorthand fails every POST, as [Web API and hosting](03-web-api-and-hosting.md) records. Demo mode is the default way to work. Backend changes need a manual restart.

**Production.**
```bash
npm --prefix web ci
npm --prefix web run build
uv run scout serve
```

**Verification.**
- **Vitest, pure logic:** the Demo Run feed reaches the expected end state; replaying a feed all at once equals applying it one by one; a reset keeps `texts`; `fromLog` places the cursor per status and infers Search and Read postings; the label table covers every node in `/meta` and yields the five back-edges; progress never decreases; tool pairing is first-in-first-out.
- **`tests/test_web_api.py`, over the demo graph with `demo_delay=0`:** the whole of [Web API and hosting](03-web-api-and-hosting.md)'s table through `TestClient(app, base_url="http://127.0.0.1")`: every refusal and its shape, `caught_up` before any token, 204, `live_from`, cancel then resume, downloads, both guards, an http-only `url`, the catch-all, the contract file.
- **`scripts/smoke_web.py`, not in CI:** one browser path through a Demo Run: start, each Pause including a refused edit, reload mid-Run, stop and resume, Done, Brief. `uv run --with playwright python scripts/smoke_web.py`, using `chromium.launch(channel="msedge")`, so no browser download or repo dependency.
- **Live:** one real Run by hand before calling it done, since the demo proves the plumbing and not how real notes read.
- **Skip-list:** no pixel tests, no component-render tests, no animation assertions. `useMotion`'s rule makes state the thing to test.

**Streamlit is deleted in the last pass,** once the smoke passes, so a working UI always exists: `clients/streamlit_app.py`, `clients/streamlit_bridge.py`, the `streamlit` group, then `uv lock`.

**Dark mode, the last fog item: not in this effort.** Colours are all custom properties, so it stays cheap to add, but a second palette needs its own contrast checks against a Mon 2 Nov deadline. It goes in future scope.

**Checklist:** `docs/lld/web-ui.md` holds the passes, each leaving one check, and the order to cut in if time runs short.
